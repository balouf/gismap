import pickle
import random

import numpy as np
import zstandard as zstd

FRAME_SIZE = 1000
LEVEL = 3
MAX_BYTES = 10_000_000  # below this estimated decompressed footprint, optimize() returns a plain list


def train_dict(source, dict_size=112_640, max_samples=50_000, seed=0):
    """
    Train a zstd compression dictionary from a sample of a source.

    Parameters
    ----------
    source: :class:`~collections.abc.Sequence`
        Source to compress (must support ``len(source)`` and ``source[i]``).
    dict_size: :class:`int`, optional
        Target dict size.
    max_samples: :class:`int`, optional
        Target number of training samples.
    seed: :class:`int`, default=0
        Seed for the sampling RNG, so repeated builds are reproducible.

    Returns
    -------
    :class:`~zstandard.ZstdCompressionDict`
        Dictionary adapted to the source.
    """
    rng = random.Random(seed)
    n = len(source)
    idx = sorted(rng.sample(range(n), min(n, max_samples)))
    return zstd.train_dictionary(dict_size, [pickle.dumps(source[i]) for i in idx])


class ZList:
    """
    Compressed list with frame-based storage.

    Stores elements in compressed frames, allowing efficient memory usage
    while maintaining random access. Uses zstandard compression.

    In this version, each frame is a concatenation of individually pickled
    items prefixed by an intra-frame offset index, then compressed. Random
    access therefore unpickles a single item instead of the whole frame, and an
    optional zstd dictionary can be trained for tighter compression.

    Typical use is a two-pass build: stream items through the default
    constructor (fast, no dictionary), then call :meth:`optimize` to train a
    dictionary and recompress aggressively (or fall back to a plain list when
    the data is small enough that memory is not a concern).

    Use as a context manager for building:

        with ZList(frame_size=100) as z:
            for item in data:
                z.append(item)

    Or use the :meth:`from_iterable` method.

    Parameters
    ----------
    frame_size : :class:`int`, default=1000
        Number of elements per compressed frame.
    level: :class:`int`, default=3
        Level of compression.
    dict_data: :class:`~zstandard.ZstdCompressionDict`, optional
        Dictionary data for compression.

    Examples
    --------

    Let us build a small big list:

    >>> mylist = [c * 1000 for c in "abcdefghijklmnopqrstuvwxyz"]

    One builds a ZList out of it.

    >>> zlist = ZList.from_iterable(mylist, frame_size=10)

    Why ZLists? Because sometimes size matters: the compressed blob is far
    smaller than the raw data.

    >>> raw_bytes = sum(len(s) for s in mylist)
    >>> raw_bytes
    26000
    >>> 0 < len(zlist._blob) < raw_bytes
    True

    >>> zlist[20][-10:]
    'uuuuuuuuuu'
    >>> len(zlist)
    26
    >>> for i, line in enumerate(mylist):
    ...     assert zlist[i] == line

    A ZList can also be obtained using a context manager and successive append.

    >>> with ZList(frame_size=10, level=0) as zlist2:
    ...     for line in mylist:
    ...         zlist2.append(line)

    Once built, the list can be packed into its best storage form with
    :meth:`optimize`. A small source is returned as a plain ``list`` (memory is
    cheap, and decompressed access is faster):

    >>> isinstance(zlist.optimize(), list)
    True

    A tight memory budget keeps it compressed as a ZList instead:

    >>> isinstance(zlist.optimize(max_bytes=1000), ZList)
    True
    """

    __slots__ = (
        "frame_size",
        "level",
        "dict_data",
        "_blob",
        "_blob_index",
        "_frame",
        "_frame_index",
        "_frame_pos",
        "_n",
        "_cctx",
        "_dctx",
    )

    def __init__(self, frame_size=FRAME_SIZE, level=LEVEL, dict_data=None):
        self.frame_size = frame_size
        self.level = level
        self.dict_data = dict_data

        self._blob = None  # concatenation of zstd frames
        self._blob_index = None  # frame pointers

        self._frame = None  # concatenation of pickled items
        self._frame_index = None  # intra-frame item pointers
        self._frame_pos = None  # opened frame

        self._n = None  # for len
        self._cctx = None
        self._dctx = zstd.ZstdDecompressor(dict_data=dict_data)

    def __getstate__(self):
        dict_data = self.dict_data.as_bytes() if self.dict_data is not None else None
        return self.frame_size, self.level, dict_data, self._blob, self._blob_index, self._n

    def __setstate__(self, state):
        dict_data = state[2]
        if dict_data is not None:
            dict_data = zstd.ZstdCompressionDict(dict_data)
        self.__init__(frame_size=state[0], level=state[1], dict_data=dict_data)
        self._blob = state[3]
        self._blob_index = state[4]
        self._n = state[5]

    def estimated_uncompressed_size(self, fudge=4):
        """
        Estimate the in-RAM footprint (in bytes) of the decompressed items.

        The uncompressed size of each zstd frame is read straight from its
        header (no decompression required), then scaled by `fudge` to account
        for the overhead of live Python objects compared to their pickled bytes.
        For the dataclass items that flow through a source, the live footprint
        measures about 3.8x the pickled bytes, so the default of 4 keeps the
        estimate a safe upper bound; deeply nested payloads may need a larger value.

        Parameters
        ----------
        fudge: :class:`int` or :class:`float`, default=4
            Multiplier approximating the live-object overhead over pickled bytes.

        Returns
        -------
        :class:`int`
            Estimated footprint in bytes.
        """
        pickled = sum(
            zstd.get_frame_parameters(self._blob[self._blob_index[f] : self._blob_index[f + 1]]).content_size
            for f in range(len(self._blob_index) - 1)
        )
        return pickled * fudge

    def optimize(self, frame_size=10, level=19, threshold=10000, max_bytes=MAX_BYTES):
        """
        Return the source in its best storage form for its size.

        When the estimated decompressed footprint is below `max_bytes`, the items
        are returned as a plain :class:`list`: memory is not a concern at that
        size, and a decompressed list avoids the per-access decompression and
        unpickling cost of a ZList. Otherwise the list is rebuilt as a compressed
        ZList using the provided `frame_size` / `level`. When `dict_data` is not
        set and the list contains more than `threshold` items, a zstd dictionary
        is trained to improve compression.

        Parameters
        ----------
        frame_size : :class:`int`, default=10
            Number of elements per compressed frame (ZList path only).
        level: :class:`int`, default=19
            Level of compression (ZList path only).
        threshold: :class:`int`, default=10000
            Train a (missing) dictionary only above this size threshold (in items).
        max_bytes: :class:`int`, default=10_000_000
            Below this estimated decompressed footprint, return a plain list.

        Returns
        -------
        :class:`list` or :class:`~gismap.utils.zlist.ZList`
            A plain list for small sources, a recompressed ZList otherwise.
        """
        if self.estimated_uncompressed_size() < max_bytes:
            return [*self]
        dict_data = self.dict_data
        if dict_data is None and self._n > threshold:
            dict_data = train_dict(self)
        return ZList.from_iterable(self, frame_size=frame_size, level=level, dict_data=dict_data)

    def __enter__(self):
        self._blob = bytearray()
        self._blob_index = [0]
        self._frame = bytearray()
        self._frame_index = [0]

        self._n = 0
        self._cctx = zstd.ZstdCompressor(level=self.level, dict_data=self.dict_data)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._merge_batch()
        self._blob = bytes(self._blob)
        self._blob_index = np.array(self._blob_index, dtype=int)
        self._cctx = None

    def load_frame(self, f):
        self._frame = self._dctx.decompress(self._blob[self._blob_index[f] : self._blob_index[f + 1]])
        sizep = np.frombuffer(self._frame, dtype=np.dtype("<u4"), count=1)[0] // 4
        self._frame_index = np.frombuffer(self._frame, dtype=np.dtype("<u4"), count=sizep)
        self._frame_pos = f

    def append(self, entry):
        """
        Add an element to the list.

        Parameters
        ----------
        entry: object
            Element to add.
        """
        self._frame += pickle.dumps(entry)
        self._frame_index.append(len(self._frame))
        self._n += 1
        if len(self._frame_index) == self.frame_size + 1:
            self._merge_batch()

    def _merge_batch(self):
        if len(self._frame_index) > 1:
            self._frame_index = np.array(self._frame_index) + 4 * (len(self._frame_index))
            if self._frame_index[-1] > 2**31:
                raise ValueError("Frame too large, decrease frame_size")
            self._frame = bytes(np.asarray(self._frame_index, dtype="<u4").tobytes() + self._frame)
            self._blob += self._cctx.compress(self._frame)
            self._blob_index.append(len(self._blob))
            self._frame = bytearray()
            self._frame_index = [0]

    def __getitem__(self, i):
        if i < 0:
            i += self._n
        if not 0 <= i < self._n:
            # Raising IndexError out of bounds is mandatory: gismo's Corpus has no __iter__ and
            # relies on the __getitem__ sequence protocol (stop on IndexError) to iterate.
            raise IndexError(i)
        frame_pos, item_pos = i // self.frame_size, i % self.frame_size
        if frame_pos != self._frame_pos:
            self.load_frame(frame_pos)
        return pickle.loads(self._frame[self._frame_index[item_pos] : self._frame_index[item_pos + 1]])

    def __len__(self):
        return self._n

    def __iter__(self):
        for frame_pos in range(len(self._blob_index) - 1):
            self.load_frame(frame_pos)
            fi, frame = self._frame_index, self._frame
            for j in range(len(fi) - 1):
                yield pickle.loads(frame[fi[j] : fi[j + 1]])

    @classmethod
    def from_iterable(cls, items, frame_size=FRAME_SIZE, level=LEVEL, dict_data=None):
        """

        Parameters
        ----------
        items: :class:`~collections.abc.Iterable`
            What we want to ZList.
        frame_size : :class:`int`, default=1000
            Number of elements per compressed frame.
        level: :class:`int`, default=3
            Level of compression.
        dict_data: :class:`~zstandard.ZstdCompressionDict`, optional
            Dictionary data for compression.

        Returns
        -------
        :class:`~gismap.utils.zlist.ZList`
        """
        with cls(frame_size=frame_size, level=level, dict_data=dict_data) as zlist:
            for item in items:
                zlist.append(item)
        return zlist
