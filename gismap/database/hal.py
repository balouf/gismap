import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import ClassVar
from urllib.parse import quote_plus

from gismap.database.blueprint import DBAuthor, clean_aliases
from gismap.utils.common import unlist
from gismap.utils.requests import autosession, auto_retry_get

HAL_TYPES = {'ART': 'journal',
             'COMM': 'conference',
             'OUV': 'book',
             'COUV': 'chapter',
             'THESE': 'thesis',
             'UNDEFINED': 'report',
}


@dataclass(repr=False)
class HALAuthor(DBAuthor):
    db_name: ClassVar[str] = 'hal'

    pid: int = None
    """Personal Id, an integer that can be used when hal-id is not available."""
    alt_pids: list = field(default_factory=list)
    """One author has one unique hal-id but possibly multiple Personal Ids. Extra pids should be put here."""

    @property
    def url(self):
        if self.id:
            return f"https://hal.science/search/index/?q=*&authIdHal_s={self.id}"
        elif self.pid:
            return f"https://hal.science/search/index/?q=*&authIdPerson_i={self.pid}"
        return f'https://hal.science/search/index?q={quote_plus(self.name)}'

    @property
    def is_set(self):
        return self.id is not None or self.pid is not None

    def update_values(self, author):
        super().update_values(author)
        self.pid = author.pid
        self.alt_pids = author.alt_pids

    @staticmethod
    def parse_entry(r):
        """
        Parameters
        ----------
        r: :class:`dict`
            Raw dict of a result (paper).

        Returns
        -------
        :class:`dict`
            The paper as a sanitized dictionary.
        """
        rosetta = {'title_s': 'title', 'abstract_s': 'abstract', 'docid': 'key',
                   'bookTitle_s': 'booktitle', 'conferenceTitle_s': 'conference', 'journalTitle_s': 'journal',
                   'docType_s': 'type', 'producedDateY_i': 'year', 'uri_s': 'url'}
        res = {v: unlist(r[k]) for k, v in rosetta.items() if k in r}
        res['authors'] = [parse_facet_author(a) for a in r.get('authFullNamePersonIDIDHal_fs', [])]
        for tag in ['booktitle', 'journal', 'conference']:
            if tag in res:
                res['venue'] = res[tag]
                break
        else:
            res['venue'] = 'unpublished'
        res['type'] = HAL_TYPES.get(res['type'], res['type'].lower())
        res['origin'] = 'hal'
        return res

    def query_id(self, s=None):
        """
        Parameters
        ----------
        s: :class:`~requests.Session`, optional
            Session.

        Returns
        -------
        :class:`list`
            Potential matches.

        Examples
        --------

        >>> fabien = HALAuthor("Fabien Mathieu")
        >>> fabien
        HALAuthor(name='Fabien Mathieu')
        >>> fabien.url
        'https://hal.science/search/index?q=Fabien+Mathieu'
        >>> fabien.populate_id()
        1
        >>> fabien
        HALAuthor(name='Fabien Mathieu', id='fabien-mathieu')
        >>> fabien.url
        'https://hal.science/search/index/?q=*&authIdHal_s=fabien-mathieu'
        >>> laurent = HALAuthor("Laurent Viennot")
        >>> laurent.query_id()
        [HALAuthor(name='Laurent Viennot', id='laurentviennot')]
        >>> unknown = HALAuthor("NotaSearcherName")
        >>> unknown
        HALAuthor(name='NotaSearcherName')
        >>> unknown.populate_id()
        0
        >>> unknown
        HALAuthor(name='NotaSearcherName')
        >>> ana = HALAuthor("Ana Busic")
        >>> ana.populate_id()
        1
        >>> ana
        HALAuthor(name='Ana Busic', id='anabusic', aliases=['Ana Bušić', 'Bušić Ana'])
        >>> diego = HALAuthor("Diego Perino") # doctest:  +NORMALIZE_WHITESPACE
        >>> diego.query_id()
        [HALAuthor(name='Diego Perino', pid=847558), HALAuthor(name='Diego Perino', pid=978810)]
        >>> HALAuthor(name='Diego Perino', pid=978810).url
        'https://hal.science/search/index/?q=*&authIdPerson_i=978810'
        """
        s = autosession(s)
        hal_api = "https://api.archives-ouvertes.fr/ref/author/"
        fields = ",".join(['label_s', 'idHal_s', 'person_i'])
        hal_args = {'q': self.name, 'fl': fields, 'wt': 'json'}
        r = auto_retry_get(s, hal_api, params=hal_args)
        response = json.loads(r.text)['response']
        hids = defaultdict(set)
        pids = defaultdict(set)
        for a in response.get('docs', []):
            if 'label_s' in a:
                if 'idHal_s' in a:
                    hids[a['idHal_s']].add(a.get('label_s'))
                elif 'person_i' in a:
                    pids[a['person_i']].add(a.get('label_s'))
        return [HALAuthor(name=self.name, id=k, aliases=clean_aliases(self.name, v)) for k, v in hids.items()] + \
            [HALAuthor(name=self.name, pid=k, aliases=clean_aliases(self.name, v)) for k, v in pids.items()]

    def query_publications(self, s=None):
        """
        Parameters
        ----------
        s: :class:`~requests.Session`, optional
            Session.

        Returns
        -------
        :class:`list`
            Papers available in HAL.

        Examples
        --------

        >>> fabien = HALAuthor(name='Fabien', id='fabien-mathieu')
        >>> publications = sorted(fabien.query_publications(),
        ...                 key=lambda p: p['title'])
        >>> publications[2] # doctest:  +NORMALIZE_WHITESPACE
        {'title': 'Achievable Catalog Size in Peer-to-Peer Video-on-Demand Systems',
        'abstract': 'We analyze a system where $n$ set-top boxes with same upload and storage capacities collaborate to
        serve $r$ videos simultaneously (a typical value is $r=n$). We give upper and lower bounds on the catalog size
        of the system, i.e. the maximal number of distinct videos that can be stored in such a system so that any demand
        of at most $r$ videos can be served. Besides $r/n$, the catalog size is constrained by the storage capacity, the
        upload capacity, and the maximum number of simultaneous connections a box can open. We show that the achievable
        catalog size drastically increases when the upload capacity of the boxes becomes strictly greater than the
        playback rate of videos.', 'key': '471724',
        'conference': 'Proceedings of the 7th Internnational Workshop on Peer-to-Peer Systems (IPTPS)',
        'type': 'conference', 'year': 2008, 'url': 'https://inria.hal.science/inria-00471724v1',
        'authors': [HALAuthor(name='Yacine Boufkhad', id='yacine-boufkhad', pid=7352),
        HALAuthor(name='Fabien Mathieu', id='fabien-mathieu', pid=446),
        HALAuthor(name='Fabien de Montgolfier', pid=949013), HALAuthor(name='Diego Perino'),
        HALAuthor(name='Laurent Viennot', id='laurentviennot', pid=1841)],
        'venue': 'Proceedings of the 7th Internnational Workshop on Peer-to-Peer Systems (IPTPS)', 'origin': 'hal'}
        >>> publications[-7] # doctest:  +NORMALIZE_WHITESPACE
        {'title': 'Upper bounds for stabilization in acyclic preference-based systems',
        'abstract': 'Preference-based systems (p.b.s.) describe interactions between nodes of a system that can rank
        their neighbors. Previous work has shown that p.b.s. converge to a unique locally stable matching if an
        acyclicity property is verified. In the following we analyze acyclic p.b.s. with respect to the
        self-stabilization theory. We prove that the round complexity is bounded by n/2 for the adversarial daemon.
        The step complexity is equivalent to (n^2)/4 for the round robin daemon, and exponential for the general
        adversarial daemon.', 'key': '668356',
        'conference': "SSS'07 - 9th international conference on Stabilization, Safety,
        and Security of Distributed Systems",
        'type': 'conference', 'year': 2007, 'url': 'https://inria.hal.science/hal-00668356v1',
        'authors': [HALAuthor(name='Fabien Mathieu', id='fabien-mathieu', pid=446)],
        'venue': "SSS'07 - 9th international conference on Stabilization, Safety,
        and Security of Distributed Systems", 'origin': 'hal'}

        Case of someone with multiple ids one want to cumulate:

        >>> emilios = HALAuthor('Emilio Calvanese').query_id()
        >>> emilios # doctest: +NORMALIZE_WHITESPACE
        [HALAuthor(name='Emilio Calvanese', aliases=['Calvanese Strinati Emilio',
        'Emilio Calvanese Strinati'], pid=911234)]
        >>> len(emilios[0].query_publications())
        69

        Note: an error is raised if not enough data is provided

        >>> HALAuthor('Fabien Mathieu').query_publications()
        Traceback (most recent call last):
        ...
        ValueError: HALAuthor(name='Fabien Mathieu') must have id or pid for publications to be fetched.
        """
        s = autosession(s)
        api = "https://api.archives-ouvertes.fr/search/"
        fields = ['docid', 'abstract_s', 'label_s', 'uri_s', '*Title_s', 'title_s',
                  'producedDateY_i', 'auth_s', 'authFullNamePersonIDIDHal_fs', 'docType_s']
        params = {'fl': fields, 'rows': 2000, 'wt': 'json'}
        if self.id:
            params['q'] = f"authIdHal_s:{self.id}"
        elif self.pid:
            params['q'] = f"authIdPerson_i:{self.pid}"
        else:
            raise ValueError(f"{self} must have id or pid for publications to be fetched.")
        r = auto_retry_get(s, api, params=params)
        response = json.loads(r.text)['response']
        res = [self.parse_entry(r) for r in response.get('docs', [])]
        for alt in self.alt_pids:
            res += HALAuthor(name=self.name, pid=alt).query_publications(s)
        return res


def parse_facet_author(a):
    """
    Parameters
    ----------
    a: :class:`str`
        Formatted APH author string from HAL API.

    Returns
    -------
    :class:`~gismap.database.hal.HALAuthor`
        Sanitized version.
    """
    name, pid, hid = a.split('_FacetSep_')
    pid = int(pid) if pid and int(pid) else None
    hid = hid if hid else None
    return HALAuthor(name=name, id=hid, pid=pid)
