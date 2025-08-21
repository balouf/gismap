import unicodedata
from bof.fuzz import Process
from gismap.sources.hal import HALAuthor
from gismap.sources.dblp import DBLPAuthor
from gismap.lab import LabAuthor, Lab


def asciify(texte):
    # Décompose les caractères en base + accents
    texte_decompose = unicodedata.normalize('NFD', texte)
    # Garde seulement les caractères qui ne sont pas des marques diacritiques (accents)
    texte_sans_accents = ''.join(
        c for c in texte_decompose
        if unicodedata.category(c) != 'Mn'
    )
    return texte_sans_accents

# Exemple
texte = "Ana Bušić"
print(asciify(texte))  # Affiche "Ana Busic"


def score_author_source(dbauthor):
    if isinstance(dbauthor, HALAuthor):
        if dbauthor.key_type == "fullname":
            return -1
        elif dbauthor.key_type == "pid":
            return 2
        else:
            return 3
    elif isinstance(dbauthor, DBLPAuthor):
        return 1
    else:
        return 0


import numpy as np


def labify_authors(db_authors, length_impact=.2, threshold=55, n_range=4):
    names = [asciify(a['author'].name) for a in db_authors.values()]
    keys = {i: k for i, k in enumerate(db_authors.keys())}
    done = np.zeros(len(names), dtype=bool)

    p = Process(length_impact=length_impact, n_range=n_range)
    p.fit(names)
    sims = p.transform(names)
    res = []
    for i, k in enumerate(db_authors.keys()):
        if done[i]:
            continue
        name = names[i]
        locs = np.where(sims[i, :] > threshold)[0]
        sources = sorted([db_authors[keys[j]]['author'] for j in locs], key=lambda a: -score_author_source(a))
        weight = sum(db_authors[keys[j]]['weight'] for j in locs)
        res.append((LabAuthor.from_sources(sources), weight))
        done[locs] = True
    return res

# res = [a for a, w in sorted(res, key=lambda aw: -aw[1])[:10]]

from gismap.sources.multi import regroup_authors, regroup_publications
from gismap.utils.logger import logger


class CoLab(Lab):
    def __init__(self, core, *args, blacklist=None, **kwargs):
        self.core = core
        if blacklist is None:
            blacklist = set()
        self.blacklist = blacklist
        super().__init__(*args, **kwargs)

    def _author_iterator(self):
        return self.core

    @property
    def all_author_keys(self):
        if self.authors is None:
            return {}
        return {
            k for a in self.authors.values()
            for k in [a.key, a.name, *a.aliases] + [kk for aa in a.sources for kk in [aa.key, aa.name, *aa.aliases]]
        }

    @property
    def all_pub_authors(self):
        if self.publications is None:
            return {}
        pub_authors = dict()
        if self.publications is not None:
            for publi in self.publications.values():
                for source in publi.sources:
                    for author in source.authors:
                        key = author.key
                        if key in pub_authors:
                            pub_authors[key]['weight'] += 1
                        else:
                            pub_authors[key] = {'author': author, 'weight': 1}
        return pub_authors

    def build(self, target=10):
        self.update_authors()
        self.update_publis()
        while len(self.authors) < target:
            spare = target - len(self.authors)
            logger.info(f"Still {spare} authors to build.")
            exists = self.all_author_keys | self.blacklist
            logger.info(f"{len(exists)} existing keys.")
            prospects = labify_authors(self.all_pub_authors)
            logger.info(f"{len(prospects)} potential lab authors found.")
            news = {a.key: a for a, w in
                    sorted([r for r in prospects if all(aa.key not in exists for aa in r[0].sources)],
                           key=lambda aw: -aw[1])[:spare]}
            self.authors.update(news)
            logger.info(f"{len(news)} new authors selected")
            if len(news) == 0:
                logger.warning("Expansion failed: no new author found.")
                break
            logger.info(f"Updating publications for new authors")
            pubs = dict()
            for author in news.values():
                author.auto_img()
                pubs.update(author.get_publications(clean=False))

            for pub in self.publications.values():
                for source in pub.sources:
                    pubs[source.key] = source
            self.publications = regroup_publications(pubs)

            redirection = {k: a for a in self.authors.values() for s in a.sources
                           for k in [s.key, s.name, *s.aliases]}
            for pub in self.publications.values():
                pub.authors = [labify_author(a, redirection) for a in pub.authors]


def labify_author(author, rosetta):
    if isinstance(author, LabAuthor):
        return author
    return rosetta.get(author.key, author)


