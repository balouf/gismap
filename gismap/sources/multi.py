from dataclasses import dataclass, field
from bof.fuzz import Process
import numpy as np

from gismap.sources.models import Publication, Author
from gismap.utils.text import clean_aliases


def score_author_source(dbauthor):
    if dbauthor.db_name == "hal":
        if dbauthor.key_type == "fullname":
            return -1
        elif dbauthor.key_type == "pid":
            return 2
        else:
            return 3
    elif dbauthor.db_name == "dblp":
        return 1
    else:
        return 0


def sort_author_sources(sources):
    return sorted(sources, key=score_author_source, reverse=True)


@dataclass(repr=False)
class SourcedAuthor(Author):
    sources: list = field(default_factory=list)

    @property
    def key(self):
        if self.sources:
            return self.sources[0].key
        else:
            return None

    @property
    def aliases(self):
        if self.sources:
            return clean_aliases(
                self.name, [n for a in self.sources for n in [a.name] + a.aliases]
            )
        else:
            return []

    @classmethod
    def from_sources(cls, sources):
        sources = sort_author_sources(sources)
        return cls(name=sources[0].name, sources=sources)

    def get_publications(self, clean=True, selector=None):
        if selector is None:
            selector = []
        res = {
            p.key: p for a in self.sources for p in a.get_publications() if all(f(p) for f in selector)
        }
        if clean:
            regroup_authors({self.key: self}, res)
            return regroup_publications(res)
        else:
            return res


publication_score_rosetta = {
    "db_name": {"dblp": 1, "hal": 2},
    "venue": {"CoRR": -1, "unpublished": -2},
    "type": {"conference": 1, "journal": 2},
}


def score_publication_source(source):
    scores = [
        v.get(getattr(source, k, None), 0) for k, v in publication_score_rosetta.items()
    ]
    scores.append(source.year)
    return tuple(scores)


def sort_publication_sources(sources):
    return sorted(sources, key=score_publication_source, reverse=True)


@dataclass(repr=False)
class SourcedPublication(Publication):
    sources: list = field(default_factory=list)

    @property
    def key(self):
        if self.sources:
            return self.sources[0].key
        else:
            return None

    @classmethod
    def from_sources(cls, sources):
        sources = sort_publication_sources(sources)
        main = sources[0]
        res = cls(
            **{
                k: getattr(main, k)
                for k in ["title", "authors", "venue", "type", "year"]
            },
            sources=sources,
        )
        return res


def regroup_authors(auth_dict, pub_dict):
    """
    Replace authors of publications with matching authors.
    Typical use: upgrade DB-specific authors to multisource authors.

    Replacement is in place.

    Parameters
    ----------
    auth_dict: :class:`dict`
        Authors to unify.
    pub_dict: :class:`dict`
        Publications to unify.

    Returns
    -------
    None
    """
    redirection = {
        k: a
        for a in auth_dict.values()
        for s in a.sources
        for k in [s.key, s.name, *s.aliases]
    }

    for pub in pub_dict.values():
        pub.authors = [redirection.get(a.key, a) for a in pub.authors]


def regroup_publications(pub_dict, threshold=85, length_impact=0.05, n_range=5):
    """
    Puts together copies of the same publication.

    Parameters
    ----------
    pub_dict: :class:`dict`
        Publications to unify.
    threshold: float
        Similarity parameter.
    length_impact: float
        Length impact parameter.

    Returns
    -------
    :class:`dict`
        Unified publications.
    """
    pub_list = [p for p in pub_dict.values()]
    res = dict()

    if pub_list:

        p = Process(length_impact=length_impact, n_range=n_range)
        p.fit([paper.title for paper in pub_list])

        done = np.zeros(len(pub_list), dtype=bool)
        for i, paper in enumerate(pub_list):
            if done[i]:
                continue
            locs = np.where(p.transform([paper.title])[0, :] > threshold)[0]
            pub = SourcedPublication.from_sources([pub_list[i] for i in locs])
            res[pub.key] = pub
            done[locs] = True
    return res
