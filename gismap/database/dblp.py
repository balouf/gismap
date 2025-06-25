from dataclasses import dataclass
from typing import ClassVar
from time import sleep
from urllib.parse import quote_plus

from bs4 import BeautifulSoup as Soup

from gismap.database.blueprint import DBAuthor, clean_aliases
from gismap.utils.requests import autosession, auto_retry_get


DBLP_TYPES = {'article': 'journal',
              'inproceedings': 'conference',
              'proceedings': 'book',
              'informal': 'report',
              'phdthesis': 'thesis',
              'habil': 'hdr',
              'software': 'software'}


@dataclass(repr=False)
class DBLPAuthor(DBAuthor):
    db_name: ClassVar[str] = 'dblp'
    query_id_backoff: ClassVar[float] = 7.0
    query_publications_backoff: ClassVar[float] = 2.0

    @property
    def url(self):
        if self.id:
            return f'https://dblp.org/pid/{self.id}.html'
        return f'https://dblp.org/search?q={quote_plus(self.name)}'

    @staticmethod
    def parse_entry(r):
        """
        Parameters
        ----------
        r: :class:`~bs4.BeautifulSoup`
            Soup of a result (paper).

        Returns
        -------
        :class:`dict`
            The paper as a dictionary.
        """
        p = r.find()
        typ = p.get('publtype', p.name)
        typ = DBLP_TYPES.get(typ, typ)
        res = {'type': typ,
               'key': p['key'],
               'url': f"https://dblp.org/rec/{p['key']}.html"}
        keys = ['title', 'booktitle', 'pages', 'journal', 'year', 'volume', 'number']
        for tag in keys:
            t = p.find(tag)
            if t:
                try:
                    res[tag] = int(t.text)
                except ValueError:
                    res[tag] = t.text
        for tag in ['booktitle', 'journal']:
            t = p.find(tag)
            if t:
                res['venue'] = t.text
                break
        else:
            res['venue'] = 'unpublished'
        res['authors'] = [DBLPAuthor(id=a['pid'], name=a.text)
                          for a in p('author')]
        res['origin'] = 'dblp'
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

        >>> fabien = DBLPAuthor("Fabien Mathieu")
        >>> fabien
        DBLPAuthor(name='Fabien Mathieu')
        >>> fabien.url
        'https://dblp.org/search?q=Fabien+Mathieu'
        >>> fabien.populate_id()
        1
        >>> fabien
        DBLPAuthor(name='Fabien Mathieu', id='66/2077')
        >>> fabien.url
        'https://dblp.org/pid/66/2077.html'
        >>> sleep(2)
        >>> manu = DBLPAuthor("Manuel Barragan")
        >>> manu.query_id() # doctest:  +NORMALIZE_WHITESPACE
        [DBLPAuthor(name='Manuel Barragan', id='07/10587', aliases=['José M. Peña 0003',
        'José Manuel Peña 0002', 'José Manuel Peñá-Barragán']),
        DBLPAuthor(name='Manuel Barragan', id='83/3865', aliases=['Manuel J. Barragan Asian', 'Manuel J. Barragán']),
        DBLPAuthor(name='Manuel Barragan', id='188/0198', aliases=['Manuel Barragán-Villarejo'])]
        >>> sleep(2)
        >>> unknown = DBLPAuthor("NotaSearcherName")
        >>> unknown
        DBLPAuthor(name='NotaSearcherName')
        >>> unknown.populate_id()
        0
        >>> unknown
        DBLPAuthor(name='NotaSearcherName')
        """
        s = autosession(s)
        dblp_api = "https://dblp.org/search/author/api"
        dblp_args = {'q': self.name}
        r = auto_retry_get(s, dblp_api, params=dblp_args)
        soup = Soup(r.text, features='xml')
        return [DBLPAuthor(name=self.name, id=hit.url.text.split('pid/')[1],
                           aliases=clean_aliases(self.name, [hit.author.text] + [alia.text for alia in hit('alias')]))
                for hit in soup('hit')]

    def query_publications(self, s=None):
        """
        Parameters
        ----------
        s: :class:`~requests.Session`, optional
            Session.

        Returns
        -------
        :class:`list`
            Papers available in DBLP.

        Examples
        --------

        >>> fabien = DBLPAuthor('Fabien Mathieu', id='66/2077')
        >>> publications = sorted(fabien.query_publications(),
        ...                 key=lambda p: p['title'])
        >>> publications[0] # doctest:  +NORMALIZE_WHITESPACE
        {'type': 'conference', 'key': 'conf/iptps/BoufkhadMMPV08',
        'url': 'https://dblp.org/rec/conf/iptps/BoufkhadMMPV08.html',
        'title': 'Achievable catalog size in peer-to-peer video-on-demand systems.',
        'booktitle': 'IPTPS', 'pages': 4, 'year': 2008, 'venue': 'IPTPS',
        'authors': [DBLPAuthor(name='Yacine Boufkhad', id='75/5742'), DBLPAuthor(name='Fabien Mathieu', id='66/2077'),
        DBLPAuthor(name='Fabien de Montgolfier', id='57/6313'), DBLPAuthor(name='Diego Perino', id='03/3645'),
        DBLPAuthor(name='Laurent Viennot', id='v/LaurentViennot')], 'origin': 'dblp'}
        >>> publications[-1] # doctest:  +NORMALIZE_WHITESPACE
        {'type': 'conference', 'key': 'conf/sss/Mathieu07',
        'url': 'https://dblp.org/rec/conf/sss/Mathieu07.html',
        'title': 'Upper Bounds for Stabilization in Acyclic Preference-Based Systems.',
        'booktitle': 'SSS', 'pages': '372-382', 'year': 2007, 'venue': 'SSS',
        'authors': [DBLPAuthor(name='Fabien Mathieu', id='66/2077')], 'origin': 'dblp'}
        """
        s = autosession(s)
        r = auto_retry_get(s, f'https://dblp.org/pid/{self.id}.xml')
        soup = Soup(r.text, features='xml')
        return [self.parse_entry(r) for r in soup('r')]
