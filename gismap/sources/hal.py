from typing import ClassVar
from dataclasses import dataclass, field
from collections import defaultdict
from urllib.parse import quote_plus
from bs4 import BeautifulSoup as Soup
import json

from gismap.sources.models import DB, Publication, Author  #  DBAuthor, DBPublication
from gismap.utils.text import clean_aliases
from gismap.utils.requests import get
from gismap.utils.common import unlist


@dataclass(repr=False)
class HAL(DB):
    db_name: ClassVar[str] = "hal"

    @classmethod
    def search_author(cls, name):
        """
        Parameters
        ----------
        name: :class:`str`
            People to find.

        Returns
        -------
        :class:`list`
            Potential matches.

        Examples
        --------

        >>> fabien = HAL.search_author("Fabien Mathieu")
        >>> fabien
        [HALAuthor(name='Fabien Mathieu', key='fabien-mathieu')]
        >>> fabien = fabien[0]
        >>> fabien.url
        'https://hal.science/search/index/?q=*&authIdHal_s=fabien-mathieu'
        >>> HAL.search_author("Laurent Viennot")[0]
        HALAuthor(name='Laurent Viennot', key='laurentviennot')
        >>> HAL.search_author("NotaSearcherName")
        []
        >>> HAL.search_author("Ana Busic")
        [HALAuthor(name='Ana Busic', key='anabusic')]
        >>> HAL.search_author("Potop-Butucaru Maria")  # doctest:  +NORMALIZE_WHITESPACE
        [HALAuthor(name='Potop-Butucaru Maria', key='858256', key_type='pid'),
        HALAuthor(name='Potop-Butucaru Maria', key='841868', key_type='pid')]
        >>> diego = HAL.search_author("Diego Perino")
        >>> diego  # doctest:  +NORMALIZE_WHITESPACE
        [HALAuthor(name='Diego Perino', key='847558', key_type='pid'),
        HALAuthor(name='Diego Perino', key='978810', key_type='pid')]
        >>> diego[1].url
        'https://hal.science/search/index/?q=*&authIdPerson_i=978810'
        """
        hal_api = "https://api.archives-ouvertes.fr/ref/author/"
        fields = ",".join(["label_s", "idHal_s", "person_i", "fullName_s"])
        hal_args = {"q": name, "fl": fields, "wt": "json"}
        r = get(hal_api, params=hal_args)
        response = json.loads(r)["response"]
        hids = defaultdict(set)
        pids = defaultdict(set)
        names = set()
        for a in response.get("docs", []):
            if "label_s" in a:
                if "idHal_s" in a:
                    hids[a["idHal_s"]].add(a.get("label_s"))
                elif "person_i" in a:
                    pids[a["person_i"]].add(a.get("label_s"))
            elif "fullName_s" in a:
                names.add(a["fullName_s"])
        res = [
            HALAuthor(name=name, key=k, aliases=clean_aliases(name, v))
            for k, v in hids.items()
        ] + [
            HALAuthor(
                name=name, key=str(k), aliases=clean_aliases(name, v), key_type="pid"
            )
            for k, v in pids.items()
        ]
        return (
            res
            if res
            else [
                HALAuthor(
                    name=name,
                    key=fullname,
                    aliases=clean_aliases(name, fullname),
                    key_type="fullname",
                )
                for fullname in names
            ]
        )

    @classmethod
    def from_author(cls, a):
        """
        Parameters
        ----------
        a: :class:`~gismap.sources.hal.HALAuthor`
            Hal researcher.

        Returns
        -------
        :class:`list`
            Papers available in HAL.

        Examples
        --------

        >>> fabien = HAL.search_author("Fabien Mathieu")[0]
        >>> publications = sorted(fabien.get_publications(), key=lambda p: p.title)
        >>> publications[2] # doctest:  +NORMALIZE_WHITESPACE
        HALPublication(title='Achievable Catalog Size in Peer-to-Peer Video-on-Demand Systems',
        authors=[HALAuthor(name='Yacine Boufkhad', key='yacine-boufkhad'),
        HALAuthor(name='Fabien Mathieu', key='fabien-mathieu'),
        HALAuthor(name='Fabien de Montgolfier', key='949013', key_type='pid'),
        HALAuthor(name='Diego Perino', key='Diego Perino', key_type='fullname'),
        HALAuthor(name='Laurent Viennot', key='laurentviennot')],
        venue='Proceedings of the 7th Internnational Workshop on Peer-to-Peer Systems (IPTPS)', type='conference',
        year=2008, key='471724', url='https://inria.hal.science/inria-00471724v1')
        >>> diego = publications[2].authors[3]
        >>> diego
        HALAuthor(name='Diego Perino', key='Diego Perino', key_type='fullname')
        >>> len(diego.get_publications())
        28
        >>> publications[-7] # doctest:  +NORMALIZE_WHITESPACE
        HALPublication(title='Upper bounds for stabilization in acyclic preference-based systems',
        authors=[HALAuthor(name='Fabien Mathieu', key='fabien-mathieu')],
        venue="SSS'07 - 9th international conference on Stabilization, Safety, and Security of Distributed Systems",
        type='conference', year=2007, key='668356', url='https://inria.hal.science/hal-00668356v1')

        Case of someone with multiple ids one want to cumulate:

        >>> maria = HAL.search_author('Maria Potop-Butucaru')
        >>> maria  # doctest: +NORMALIZE_WHITESPACE
        [HALAuthor(name='Maria Potop-Butucaru', key='858256', key_type='pid'),
        HALAuthor(name='Maria Potop-Butucaru', key='841868', key_type='pid')]
        >>> len(HAL.from_author(maria[0]))
        26
        >>> len(maria[1].get_publications())
        123

        Note: an error is raised if not enough data is provided

        >>> HAL.from_author(HALAuthor('Fabien Mathieu'))
        Traceback (most recent call last):
        ...
        ValueError: HALAuthor(name='Fabien Mathieu') must have a key for publications to be fetched.
        """
        api = "https://api.archives-ouvertes.fr/search/"
        fields = [
            "docid",
            "abstract_s",
            "label_s",
            "uri_s",
            "*Title_s",
            "title_s",
            "producedDateY_i",
            "auth_s",
            "authFullNamePersonIDIDHal_fs",
            "docType_s",
        ]
        params = {"fl": fields, "rows": 2000, "wt": "json"}
        if a.key is None:
            raise ValueError(f"{a} must have a key for publications to be fetched.")
        if a.key_type == "pid":
            params["q"] = f"authIdPerson_i:{a.key}"
        elif a.key_type == "fullname":
            params["q"] = f'authFullName_s:"{a.key}"'
        else:
            params["q"] = f"authIdHal_s:{a.key}"
        r = get(api, params=params)
        response = json.loads(r)["response"]
        res = [HALPublication.from_json(r) for r in response.get("docs", [])]
        return res


@dataclass(repr=False)
class HALAuthor(Author, HAL):
    key: str | int = None
    key_type: str = None
    aliases: list = field(default_factory=list)

    @property
    def url(self):
        if self.key_type == "pid":
            return f"https://hal.science/search/index/?q=*&authIdPerson_i={self.key}"
        elif self.key_type == "fullname":
            return f"https://hal.science/search/index?q={quote_plus(self.name)}"
        else:
            return f"https://hal.science/search/index/?q=*&authIdHal_s={self.key}"

    @property
    def img(self):
        if self.key_type is not None:
            return None
        soup = Soup(get(f"https://cv.hal.science/{self.key}"), "lxml")
        if soup.form:
            return None
        try:
            return soup.main.section.div.div.div.img["src"]
        except TypeError:
            return None

    def get_publications(self):
        return HAL.from_author(self)


def parse_facet_author(a):
    """

    Parameters
    ----------
    a: :class:`str`
        Hal facet of author

    Returns
    -------
    :class:`~gismap.sources.hal.HALAuthor`

    """
    name, pid, hid = a.split("_FacetSep_")
    if hid:
        return HALAuthor(name=name, key=hid)
    elif pid and int(pid):
        return HALAuthor(name=name, key=pid, key_type="pid")
    else:
        return HALAuthor(name=name, key=name, key_type="fullname")


HAL_TYPES = {
    "ART": "journal",
    "COMM": "conference",
    "OUV": "book",
    "COUV": "chapter",
    "THESE": "thesis",
    "UNDEFINED": "report",
}

HAL_KEYS = {
    "title_s": "title",
    "abstract_s": "abstract",
    "docid": "key",
    "bookTitle_s": "booktitle",
    "conferenceTitle_s": "conference",
    "journalTitle_s": "journal",
    "docType_s": "type",
    "producedDateY_i": "year",
    "uri_s": "url",
}


@dataclass(repr=False)
class HALPublication(Publication, HAL):
    key: str
    abstract: str = None
    url: str = None

    @classmethod
    def from_json(cls, r):
        """

        Parameters
        ----------
        r: :class:`dict`
            De-serialized JSON.

        Returns
        -------
        :class:`~gismap.sources.hal.HALPublication`

        """
        res = {v: unlist(r[k]) for k, v in HAL_KEYS.items() if k in r}
        res["authors"] = [
            parse_facet_author(a) for a in r.get("authFullNamePersonIDIDHal_fs", [])
        ]
        for tag in ["booktitle", "journal", "conference"]:
            if tag in res:
                res["venue"] = res[tag]
                break
        else:
            res["venue"] = "unpublished"
        res["type"] = HAL_TYPES.get(res["type"], res["type"].lower())
        return cls(**{k: v for k, v in res.items() if k in cls.__match_args__})
