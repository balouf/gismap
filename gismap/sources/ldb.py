from dataclasses import dataclass, field
from functools import lru_cache
from typing import ClassVar
from platformdirs import user_data_dir
from pathlib import Path
import errno
import os

import zstandard as zstd
import dill as pickle
import numpy as np
import numba as nb
from bof.fuzz import Process
from gismo.common import safe_write
from tqdm.auto import tqdm

from gismap.sources.dblp_ttl import publis_streamer
from gismap.sources.models import DB, Author, Publication
from gismap.utils.logger import logger
from gismap.utils.text import asciify
from gismap.utils.zlist import ZList


DATA_DIR = Path(user_data_dir(
    appname="gismap",
    appauthor=False,
))

LDB_STEM = "ldb"

LDB_PATH = DATA_DIR / f"{LDB_STEM}.pkl.zst"

TTL_URL = "https://dblp.org/rdf/dblp.ttl.gz"


@dataclass(repr=False)
class LDB(DB):
    """
    Browse DBLP from a local copy of the database.

    LDB is a class-only database - it should not be instantiated.
    All methods are classmethods and state is stored in class variables.
    """
    db_name: ClassVar[str] = LDB_STEM
    source: ClassVar[str] = TTL_URL

    # Class-level state (replaces instance attributes)
    authors: ClassVar[ZList | None] = None
    publis: ClassVar[ZList | None] = None
    keys: ClassVar[dict | None] = None
    search_engine: ClassVar[Process | None] = None
    _initialized: ClassVar[bool] = False

    __hash__ = object.__hash__

    def __init__(self):
        raise TypeError(
            "LDB should not be instantiated. Use class methods directly, e.g., LDB.search_author(name)"
        )

    @classmethod
    def _ensure_loaded(cls):
        """Lazy-load the database if not already loaded."""
        if not cls._initialized and LDB_PATH.exists():
            cls.load_db()

    @classmethod
    def build_db(cls, source=None, limit=None, n_range=2, length_impact=.2):
        if source is None:
            source = cls.source
        authors_dict = dict()
        logger.info("Retrieve publications")
        with ZList() as publis:
            for i, (key, title, typ, authors, url, streams, pages, venue, year) in enumerate(publis_streamer(source)):
                auth_indices = []
                for auth_key, auth_name in authors.items():
                    if auth_key not in authors_dict:
                        authors_dict[auth_key] = (len(authors_dict), auth_name, [i])
                    else:
                        authors_dict[auth_key][2].append(i)
                    auth_indices.append(authors_dict[auth_key][0])
                publis.append((key, title, typ, auth_indices, url, streams, pages, venue, year))
                if i == limit:
                    break
        cls.publis = publis
        logger.info(f"{len(publis)} publications retrieved.")
        logger.info("Compact authors")
        with ZList() as authors:
            for key, (_, name, pubs) in tqdm(authors_dict.items()):
                authors.append((key, name, pubs))
        cls.authors = authors
        cls.keys = {k: v[0] for k, v in authors_dict.items()}
        del authors_dict
        cls.search_engine = Process(n_range=n_range, length_impact=length_impact)
        cls.search_engine.fit([asciify(a[1]) for a in authors])
        cls.search_engine.choices = np.arange(len(authors))
        cls.search_engine.vectorizer.features_ = cls.numbify_dict(cls.search_engine.vectorizer.features_)
        logger.info(f"{len(cls.authors)} compacted.")
        cls._invalidate_cache()
        cls._initialized = True

    @classmethod
    @lru_cache(maxsize=50000)
    def author_by_index(cls, i):
        key, name, _ = cls.authors[i]
        return LDBAuthor(key=key, name=name)

    @classmethod
    def author_by_key(cls, key):
        return cls.author_by_index(cls.keys[key])

    @classmethod
    @lru_cache(maxsize=50000)
    def publication_by_index(cls, i):
        key, title, typ, authors, url, streams, pages, venue, year = cls.publis[i]
        if venue is None:
            venue = "unpublished"
        return {"key": key, "title": title, "type": typ,
                "authors": authors,
                "url": url, "streams": streams, "pages": pages,
                "venue": venue, "year": year}

    @classmethod
    def author_publications(cls, key):
        cls._ensure_loaded()
        _, name, pubs = cls.authors[cls.keys[key]]
        pubs = [cls.publication_by_index(k).copy() for k in pubs]
        auth_ids = sorted({k for p in pubs for k in p["authors"]})
        auths = {k: cls.author_by_index(k) for k in auth_ids}
        for pub in pubs:
            pub["authors"] = [auths[k] for k in pub["authors"]]
            metadata = dict()
            for k in ["url", "streams", "pages"]:
                v = pub.pop(k)
                if v is not None:
                    metadata[k] = v
            pub["metadata"] = metadata
        return [LDBPublication(**pub) for pub in pubs]

    @classmethod
    @lru_cache(maxsize=1000)
    def search_author(cls, name, limit=5, score_cutoff=40.0, slack=10.0):
        cls._ensure_loaded()
        res = cls.search_engine.extract(asciify(name), limit=limit, score_cutoff=score_cutoff)
        res = [r[0] for r in res if r[1] > res[0][1] - slack]
        sorted_ids = {i: cls.author_by_index(i) for i in sorted(res)}
        return [sorted_ids[i] for i in res]

    @classmethod
    def _invalidate_cache(cls):
        cls.search_author.cache_clear()
        cls.publication_by_index.cache_clear()
        cls.author_by_index.cache_clear()

    @classmethod
    def from_author(cls, a):
        return cls.author_publications(a.key)

    @classmethod
    def retrieve(cls):
        raise NotImplementedError()

    @classmethod
    def dump(cls, filename: str, path=".", overwrite=False):
        """Save class state to file."""
        # Convert numba dict to regular dict for pickling
        nb_dict = None
        if cls.search_engine is not None:
            nb_dict = cls.search_engine.vectorizer.features_
            cls.search_engine.vectorizer.features_ = dict(nb_dict)

        state = {
            'authors': cls.authors,
            'publis': cls.publis,
            'keys': cls.keys,
            'search_engine': cls.search_engine,
        }

        # Use safe_write pattern from gismo.common
        destination = Path(path) / f"{Path(filename).stem}.pkl.zst"
        if destination.exists() and not overwrite:
            print(f"File {destination} already exists! Use overwrite option to overwrite.")
        else:
            with safe_write(destination) as f:
                cctx = zstd.ZstdCompressor(level=3)
                with cctx.stream_writer(f) as z:
                    pickle.dump(state, z, protocol=5)

        # Restore numba dict
        if cls.search_engine is not None:
            cls.search_engine.vectorizer.features_ = nb_dict

    @classmethod
    def load(cls, filename: str, path="."):
        """Load class state from file."""
        dest = Path(path) / f"{Path(filename).stem}.pkl.zst"
        if not dest.exists():
            dest = dest.with_suffix(".pkl")
        if not dest.exists():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), dest)

        dctx = zstd.ZstdDecompressor()
        with open(dest, "rb") as f, dctx.stream_reader(f) as z:
            state = pickle.load(z)

        cls.authors = state['authors']
        cls.publis = state['publis']
        cls.keys = state['keys']
        cls.search_engine = state['search_engine']

        if cls.search_engine is not None:
            cls.search_engine.vectorizer.features_ = cls.numbify_dict(
                cls.search_engine.vectorizer.features_
            )

        cls._invalidate_cache()
        cls._initialized = True

    @classmethod
    def dump_db(cls):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.dump(LDB_STEM, path=DATA_DIR, overwrite=True)

    @classmethod
    def load_db(cls):
        try:
            cls.load(LDB_STEM, path=DATA_DIR)
        except FileNotFoundError:
            logger.warning("No LDB installed. Build or retrieve before using.")

    @staticmethod
    def delete_db():
        if LDB_PATH.exists():
            LDB_PATH.unlink()

    @staticmethod
    def numbify_dict(input_dict):
        nb_dict = nb.typed.Dict.empty(key_type=nb.types.unicode_type, value_type=nb.types.int64)
        for k, v in input_dict.items():
            nb_dict[k] = v
        return nb_dict


@dataclass(repr=False)
class LDBAuthor(Author, LDB):
    key: str
    aliases: list = field(default_factory=list)

    @property
    def url(self):
        return f"https://dblp.org/pid/{self.key}.html"

    def get_publications(self):
        return LDB.from_author(self)



@dataclass(repr=False)
class LDBPublication(Publication, LDB):
    key: str
    metadata: dict = field(default_factory=dict)

    @property
    def url(self):
        return self.metadata.get("url", f"https://dblp.org/rec/{self.key}.html")

    @property
    def stream(self):
        if "streams" in self.metadata:
            return f'https://dblp.org/streams/{self.metadata["streams"][0]}'
        return None
