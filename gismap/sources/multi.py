from dataclasses import dataclass, field
from bof.fuzz import jit_square_factors
from bof.feature_extraction import CountVectorizer
import numpy as np

from gismap.sources.models import Publication, Author
from gismap.utils.text import clean_aliases


def score_author_source(dbauthor):
    """
    Compute a quality score for an author source.

    Higher scores indicate more reliable author identification.
    HAL idHal keys are preferred, followed by HAL pid, then DBLP/LDB.

    Parameters
    ----------
    dbauthor: :class:`~gismap.sources.models.Author`
        A database-specific author object.

    Returns
    -------
    :class:`int`
        Score value (higher is better).
    """
    if dbauthor.db_name == "hal":
        if dbauthor.key_type == "fullname":
            return -1
        elif dbauthor.key_type == "pid":
            return 2
        else:
            return 3
    elif dbauthor.db_name in ["dblp", "ldb"]:
        return 1
    else:
        return 0


def sort_author_sources(sources):
    """
    Sort author sources by quality score in descending order.

    Parameters
    ----------
    sources: :class:`list`
        List of database-specific author objects.

    Returns
    -------
    :class:`list`
        Sorted list with highest-quality sources first.
    """
    return sorted(sources, key=score_author_source, reverse=True)


@dataclass(repr=False)
class SourcedAuthor(Author):
    """
    An author aggregated from multiple database sources.

    Combines author information from HAL, DBLP, and/or LDB into a single entity.
    The primary source (first in the sorted list) determines the author's key.

    Parameters
    ----------
    name: :class:`str`
        The author's name.
    sources: :class:`list`
        List of database-specific author objects (HALAuthor, DBLPAuthor, LDBAuthor).
    """

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
        if not isinstance(selector, list):
            selector = [selector]
        res = {
            p.key: p
            for a in self.sources
            for p in a.get_publications()
            if all(f(p) for f in selector)
        }
        if clean:
            regroup_authors({self.key: self}, res)
            return regroup_publications(res)
        else:
            return res


publication_score_rosetta = {
    "db_name": {"dblp": 1, "ldb": 1, "hal": 2},
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
    """
    A publication aggregated from multiple database sources.

    Combines publication entries from HAL, DBLP, and/or LDB that refer
    to the same paper. The primary source determines the publication's metadata.

    Parameters
    ----------
    title: :class:`str`
        Publication title.
    authors: :class:`list`
        List of author objects.
    venue: :class:`str`
        Publication venue.
    type: :class:`str`
        Publication type.
    year: :class:`int`
        Publication year.
    sources: :class:`list`
        List of database-specific publication objects.
    """

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
        pub.authors = [
            redirection.get(a.key, redirection.get(a.name, a)) for a in pub.authors
        ]


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
    if len(pub_dict) == 0:
        return dict()
    pub_list = [p for p in pub_dict.values()]
    res = dict()
    vectorizer = CountVectorizer(n_range=n_range)
    x = vectorizer.fit_transform([p.title for p in pub_list])
    y = x.T.tocsr()
    jc_matrix = jit_square_factors(
        x.indices, x.indptr, y.indices, y.indptr, len(pub_list), length_impact
    )
    done = np.zeros(len(pub_list), dtype=bool)
    for i, paper in enumerate(pub_list):
        if done[i]:
            continue
        locs = np.where(jc_matrix[i, :] > threshold)[0]
        pub = SourcedPublication.from_sources([pub_list[i] for i in locs])
        res[pub.key] = pub
        done[locs] = True
    return res
