from dataclasses import dataclass
from typing import ClassVar

from gismap.utils.common import LazyRepr


@dataclass(repr=False)
class Author(LazyRepr):
    name: str


@dataclass(repr=False)
class Publication(LazyRepr):
    title: str
    authors: list
    venue: str
    type: str
    year: int


@dataclass(repr=False)
class DB(LazyRepr):
    db_name: ClassVar[str] = None
    author_backoff: ClassVar[float] = 0.0
    publi_backoff: ClassVar[float] = 0.0

    @classmethod
    def search_author(cls, name):
        raise NotImplementedError

    @classmethod
    def from_author(cls, a):
        raise NotImplementedError


