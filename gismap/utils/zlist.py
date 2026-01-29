from gismo.common import MixInIO
import zstandard as zstd
import numpy as np
import pickle

dctx = zstd.ZstdDecompressor()
cctx = zstd.ZstdCompressor()


class ZList(MixInIO):
    """
    Compressed list with frame-based storage.

    Stores elements in compressed frames, allowing efficient memory usage
    while maintaining random access. Uses zstandard compression.

    Use as a context manager for building:

        with ZList(frame_size=1000) as z:
            for item in data:
                z.append(item)

    Parameters
    ----------
    frame_size : :class:`int`, default=1000
        Number of elements per compressed frame.
    """

    def __init__(self, frame_size=1000):
        self.frame_size = frame_size
        self.frame = None
        self._frame_index = None
        self._blob = None
        self._off = None
        self._n = None
        self._batch = None

    def _merge_batch(self):
        if self._batch:
            frame = cctx.compress(pickle.dumps(self._batch))
            self._blob += frame
            self._off.append(len(self._blob))
            self._batch = []

    def append(self, entry):
        """
        Add an element to the list.

        Parameters
        ----------
        entry
            Element to add.
        """
        self._batch.append(entry)
        self._n += 1
        if len(self._batch) == self.frame_size:
            self._merge_batch()

    @property
    def size(self):
        return len(self._blob)

    def __enter__(self):
        self._blob = bytearray()
        self._off = [0]
        self._n = 0
        self._batch = []
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._merge_batch()
        self._blob = bytes(self._blob)
        self._off = np.array(self._off, dtype=int)

    def load_frame(self, f):
        self.frame = pickle.loads(
            dctx.decompress(self._blob[self._off[f] : self._off[f + 1]])
        )

    def __getitem__(self, i):
        g, f = i // self.frame_size, i % self.frame_size
        if g != self._frame_index:
            self.load_frame(g)
            self._frame_index = g
        return self.frame[f]

    def __len__(self):
        return self._n
