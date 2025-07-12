from dataclasses import dataclass, field
from bof.fuzz import Process
import numpy as np

from gismap.sources.models import Publication, Author
from gismap.utils.text import clean_aliases


score_rosetta = {
    'db_name': {'dblp': 1, 'hal': 2},
    'venue': {'CoRR': -1, 'unpublished': -2},
    'type': {'conference': 1, 'journal': 2}
}


@dataclass(repr=False)
class SourcedAuthor(Author):
    key: str
    sources: list = field(default_factory=list)
    aliases: list = field(default_factory=list)

    @classmethod
    def from_sources(cls, sources):
        main = sources[0]
        res = cls(name=main.name, key=main.key)
        res.aliases = clean_aliases(main.name, [n for a in sources for n in [a.name]+a.aliases])
        res.sources = sources
        return res

    def get_publications(self, clean=True):
        res = {p.key: p for a in self.sources for p in a.get_publications()}
        if clean:
            regroup_authors({self.key: self}, res)
            return regroup_publications(res)
        else:
            return res


@dataclass(repr=False)
class SourcedPublication(Publication):
    key: str
    sources: list = field(default_factory=list)

    @classmethod
    def from_sources(cls, sources):
        sources = sorted(sources, key=cls.score_source, reverse=True)
        main = sources[0]
        res = cls(**{k: getattr(main, k) for k in main.__dict__ if k in cls.__match_args__}, sources=sources)
        for k, v in main.__dict__.items():
            if k not in cls.__match_args__:
                setattr(res, k, v)
        return res

    @staticmethod
    def score_source(source):
        scores = [v.get(getattr(source, k, None), 0) for k, v in score_rosetta.items()]
        scores.append(source.year)
        return tuple(scores)


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
    redirection = {s.key: a for a in auth_dict.values() for s in a.sources}
    for pub in pub_dict.values():
        pub.authors = [redirection.get(a.key, a) for a in pub.authors]


def regroup_publications(pub_dict, threshold=.9, length_impact=.2):
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

    p = Process(length_impact=length_impact)
    p.fit([paper.title for paper in pub_list])

    res = dict()
    done = np.zeros(len(pub_list), dtype=bool)
    for i, paper in enumerate(pub_list):
        if done[i]:
            continue
        locs = np.where(p.transform([paper.title], threshold=threshold)[0, :] > threshold)[0]
        pub = SourcedPublication.from_sources([pub_list[i] for i in locs])
        res[pub.key] = pub
        done[locs] = True
    return res
