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
        s = autosession(s)
        dblp_api = "https://dblp.org/search/author/api"
        dblp_args = {'q': self.name}
        r = auto_retry_get(s, dblp_api, params=dblp_args)
        soup = Soup(r.text, features='xml')
        return [DBLPAuthor(name=self.name, id=hit.url.text.split('pid/')[1],
                           aliases=clean_aliases(self.name, [hit.author.text] + [alia.text for alia in hit('alias')]))
                for hit in soup('hit')]

    def query_publications(self, s=None):
        s = autosession(s)
        r = auto_retry_get(s, f'https://dblp.org/pid/{self.id}.xml')
        soup = Soup(r.text, features='xml')
        return [self.parse_entry(r) for r in soup('r')]
