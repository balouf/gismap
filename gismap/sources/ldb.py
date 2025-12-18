from dataclasses import dataclass, field
from functools import lru_cache
from typing import ClassVar
from platformdirs import user_data_dir
from pathlib import Path

import numpy as np
import numba as nb
from bof.fuzz import Process
from gismo import MixInIO
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
class LDB(DB, MixInIO):
    """
    Browse DBLP from a local copy of the database.
    """
    db_name: ClassVar[str] = LDB_STEM
    source: ClassVar[str] = TTL_URL
    __hash__ = object.__hash__

    def __init__(self):
        self.authors = None
        self.publis = None
        self.keys = None
        self.search_engine = None
        if LDB_PATH.exists():
            self.load_db_inplace()

    def build_db(self, source=None, limit=None, n_range=2, length_impact=.2):
        if source is None:
            source = self.source
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
        self.publis = publis
        logger.info(f"{len(publis)} publications retrieved.")
        logger.info("Compact authors")
        with ZList() as authors:
            for key, (_, name, pubs) in tqdm(authors_dict.items()):
                authors.append((key, name, pubs))
        self.authors = authors
        self.keys = {k: v[0] for k, v in authors_dict.items()}
        del authors_dict
        self.search_engine = Process(n_range=n_range, length_impact=length_impact)
        self.search_engine.fit([asciify(a[1]) for a in authors])
        self.search_engine.choices = np.arange(len(authors))
        self.search_engine.vectorizer.features_ = self.numbify_dict(self.search_engine.vectorizer.features_)
        logger.info(f"{len(self.authors)} compacted.")
        self._invalidate_cache()

    @lru_cache(maxsize=50000)
    def author_by_index(self, i):
        key, name, _ = self.authors[i]
        return LDBAuthor(key=key, name=name)

    def author_by_key(self, key):
        return self.author_by_index(self.keys[key])

    @lru_cache(maxsize=50000)
    def publication_by_index(self, i):
        key, title, typ, authors, url, streams, pages, venue, year = self.publis[i]
        if venue is None:
            venue = "unpublished"
        return {"key": key, "title": title, "type": typ,
                "authors": authors,
                "url": url, "streams": streams, "pages": pages,
                "venue": venue, "year": year}

    def author_publications(self, key):
        _, name, pubs = self.authors[self.keys[key]]
        pubs = [self.publication_by_index(k).copy() for k in pubs]
        auth_ids = sorted({k for p in pubs for k in p["authors"]})
        auths = {k: self.author_by_index(k) for k in auth_ids}
        for pub in pubs:
            pub["authors"] = [auths[k] for k in pub["authors"]]
            metadata = dict()
            for k in ["url", "streams", "pages"]:
                v = pub.pop(k)
                if v is not None:
                    metadata[k] = v
            pub["metadata"] = metadata
        return [LDBPublication(**pub) for pub in pubs]

    @lru_cache(maxsize=1000)
    def search_author(self, name, limit=5, score_cutoff=40.0, slack=10.0):
        res = self.search_engine.extract(asciify(name), limit=limit, score_cutoff=score_cutoff)
        res = [r[0] for r in res if r[1] > res[0][1] - slack]
        sorted_ids = {i: self.author_by_index(i) for i in sorted(res)}
        return [sorted_ids[i] for i in res]

    def _invalidate_cache(self):
        self.search_author.cache_clear()
        self.publication_by_index.cache_clear()
        self.author_by_index.cache_clear()

    def from_author(self, a):
        return self.author_publications(a.key)

    def dump(self, *args, **kwargs):
        if self.search_engine is not None:
            nb_dict = self.search_engine.vectorizer.features_
            self.search_engine.vectorizer.features_ = dict(nb_dict)
            super().dump(*args, **kwargs)
            self.search_engine.vectorizer.features_ = nb_dict
        else:
            super().dump(*args, **kwargs)

    def dump_db(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.dump(LDB_STEM, path=DATA_DIR, overwrite=True)

    @classmethod
    def load(cls, *args, **kwargs):
        res = super().load(*args, **kwargs)
        res._invalidate_cache()
        if res.search_engine is not None:
            res.search_engine.vectorizer.features_ = cls.numbify_dict(res.search_engine.vectorizer.features_)
        return res

    @classmethod
    def load_db(cls):
        try:
            return cls.load(LDB_STEM, path=DATA_DIR)
        except FileNotFoundError:
            logger.warning("No LDB installed. Build or retrieve before using.")
            return LDB()

    def load_db_inplace(self):
        other = self.load_db()
        self.publis = other.publis
        self.authors = other.authors
        self.keys = other.keys
        self.search_engine = other.search_engine
        self._invalidate_cache()

    def retrieve(self):
        raise NotImplementedError()

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


ldb = LDB()

@dataclass(repr=False)
class LDBAuthor(Author, LDB):
    key: str
    aliases: list = field(default_factory=list)

    @property
    def url(self):
        return f"https://dblp.org/pid/{self.key}.html"

    def get_publications(self):
        return ldb.from_author(self)



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
