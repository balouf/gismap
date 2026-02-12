from typing import ClassVar
from dataclasses import dataclass, field
from urllib.parse import quote_plus
from bs4 import BeautifulSoup as Soup
from time import sleep

from gismap.sources.models import DB, Author, Publication
from gismap.utils.text import clean_aliases, auto_int
from gismap.utils.requests import get


@dataclass(repr=False)
class DBLP(DB):
    db_name: ClassVar[str] = "dblp"
    author_backoff: ClassVar[float] = 5.0
    publi_backoff: ClassVar[float] = 5.0

    @classmethod
    def search_author(cls, name, wait=True):
        """
        Parameters
        ----------
        name: :class:`str`
            People to find.
        wait: :class:`bool`, default=True
            Wait a bit to avoid 429.

        Returns
        -------
        :class:`list`
            Potential matches.

        Examples
        --------

        >>> fabien = DBLP.search_author("Fabien Mathieu")
        >>> fabien
        [DBLPAuthor(name='Fabien Mathieu', key='66/2077')]
        >>> fabien[0].url
        'https://dblp.org/pid/66/2077.html'
        >>> manu = DBLP.search_author("Manuel Barragan")
        >>> manu # doctest:  +NORMALIZE_WHITESPACE
        [DBLPAuthor(name='Manuel Barragan', key='07/10587'),
        DBLPAuthor(name='Manuel Barragan', key='83/3865'),
        DBLPAuthor(name='Manuel Barragan', key='188/0198')]
        >>> DBLP.search_author("NotaSearcherName", wait=False)
        []
        """
        dblp_api = "https://dblp.org/search/author/api"
        dblp_args = {"q": name}
        r = get(dblp_api, params=dblp_args)
        soup = Soup(r, features="xml")
        if wait:
            sleep(cls.author_backoff)
        return [
            DBLPAuthor(
                name=name,
                key=hit.url.text.split("pid/")[1],
                aliases=clean_aliases(
                    name, [hit.author.text] + [alia.text for alia in hit("alias")]
                ),
            )
            for hit in soup("hit")
        ]

    @classmethod
    def from_author(cls, a, wait=True):
        """
        Returns
        -------
        :class:`list`
            Papers available in DBLP.
        wait: :class:`bool`
            Wait a bit to avoid 429.
        """
        r = get(f"https://dblp.org/pid/{a.key}.xml")
        soup = Soup(r, features="xml")
        if wait:
            sleep(cls.publi_backoff)
        res = [DBLPPublication.from_soup(r) for r in soup("r")]
        return [p for p in res if p.authors]


@dataclass(repr=False)
class DBLPAuthor(Author, DBLP):
    """
    Examples
    --------

    >>> fabien = DBLPAuthor('Fabien Mathieu', key='66/2077')
    >>> publications = sorted(fabien.get_publications(),
    ...                 key=lambda p: p.title)
    >>> publications[0].url # doctest:  +NORMALIZE_WHITESPACE
     'https://dblp.org/rec/conf/iptps/BoufkhadMMPV08.html'
    >>> publications[-1] # doctest:  +NORMALIZE_WHITESPACE
    DBLPPublication(title='Upper Bounds for Stabilization in Acyclic Preference-Based Systems.',
    authors=[DBLPAuthor(name='Fabien Mathieu', key='66/2077')], venue='SSS', type='conference', year=2007,
    key='conf/sss/Mathieu07')

    """

    key: str
    aliases: list = field(default_factory=list)

    @property
    def url(self):
        if self.key:
            return f"https://dblp.org/pid/{self.key}.html"
        return f"https://dblp.org/search?q={quote_plus(self.name)}"

    def get_publications(self, wait=True):
        return DBLP.from_author(self, wait=wait)


DBLP_TYPES = {
    "article": "journal",
    "inproceedings": "conference",
    "proceedings": "book",
    "informal": "report",
    "phdthesis": "thesis",
    "habil": "hdr",
    "software": "software",
}


@dataclass(repr=False)
class DBLPPublication(Publication, DBLP):
    """
    Publication from the DBLP database.

    Parameters
    ----------
    title: :class:`str`
        Publication title.
    authors: :class:`list`
        List of :class:`DBLPAuthor` objects.
    venue: :class:`str`
        Publication venue.
    type: :class:`str`
        Publication type.
    year: :class:`int`
        Publication year.
    key: :class:`str`
        DBLP record key.
    metadata: :class:`dict`
        Additional metadata (pages, volume, etc.).
    """

    key: str
    metadata: dict = field(default_factory=dict)

    @property
    def url(self):
        if self.key:
            return f"https://dblp.org/rec/{self.key}.html"
        else:
            return None

    @classmethod
    def from_soup(cls, soup):
        p = soup.find()
        typ = p.get("publtype", p.name)
        typ = DBLP_TYPES.get(typ, typ)

        res = {
            "type": typ,
            "key": p["key"],
            "title": p.title.text,
            "year": int(p.year.text),
        }
        for tag in ["booktitle", "journal"]:
            t = p.find(tag)
            if t:
                res["venue"] = t.text
                break
        else:
            res["venue"] = "unpublished"
        res["authors"] = [DBLPAuthor(key=a["pid"], name=a.text) for a in p("author")]

        metadata = dict()
        for tag in p.find_all(recursive=False):
            name = tag.name
            if name not in {"title", "year", "author", "booktitle", "journal"}:
                metadata[name] = auto_int(tag.text)

        return cls(**res, metadata=metadata)
