from dataclasses import dataclass, field

import numpy as np

from gismap.sources.models import Author, Publication
from gismap.utils.fuzzy import similarity_matrix
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

    Examples
    --------

    >>> from gismap.sources.models import Author, DB
    >>> from gismap.sources.hal import HALAuthor
    >>> from gismap.sources.ldb import LDBAuthor
    >>> class YADB(DB):
    ...     db_name = "YADB"
    >>> class YAAuthor(Author, YADB):
    ...     pass
    >>> authors = [HALAuthor("Titi", key="titi"), HALAuthor("Toto", key="1234"),
    ... LDBAuthor("Tata", key="tata"), YAAuthor("John Doe"),
    ... HALAuthor("Dolly", key_type="fullname")]
    >>> sorted(authors, key=score_author_source, reverse=True)  # doctest: +NORMALIZE_WHITESPACE
    [HALAuthor(name='Titi', key='titi'), HALAuthor(name='Toto', key='1234', key_type='pid'),
    LDBAuthor(name='Tata', key='tata'), YAAuthor(name='John Doe'),
    HALAuthor(name='Dolly', key_type='fullname')]
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
            return clean_aliases(self.name, [n for a in self.sources for n in [a.name] + a.aliases])
        else:
            return []

    @classmethod
    def from_sources(cls, sources):
        sources = sort_author_sources(sources)
        return cls(name=sources[0].name, sources=sources)

    def _resolve_sources(self, spec):
        if isinstance(spec, int):
            return [self.sources[spec]]
        matches = [s for s in self.sources if s.db_name == spec]
        if not matches:
            available = ", ".join(s.db_name for s in self.sources)
            raise ValueError(f"No source matching '{spec}'. Available: {available}")
        return matches

    def _label(self, spec):
        if isinstance(spec, int):
            return f"{self.sources[spec].db_name} ({spec})"
        return spec

    def _fetch_pubs(self, spec):
        sources = self._resolve_sources(spec)
        return {p.key: p for s in sources for p in s.get_publications()}

    def diff_sources(self, a, b):
        """
        Compare publications between two sources.

        Parameters
        ----------
        a : :class:`int` or :class:`str`
            First source: index in ``self.sources`` or db_name to match.
        b : :class:`int` or :class:`str`
            Second source.

        Returns
        -------
        :class:`~gismap.sources.multi.DiffResult`
            Publications found only in a and only in b.

        Examples
        --------

        >>> from gismap.lab import LabAuthor
        >>> me = LabAuthor("Fabien Mathieu (hal:fabien-mathieu, ldb:66/2077)")
        >>> diff = me.diff_sources(0, 1)  # doctest: +ELLIPSIS
        >>> diff  # doctest: +ELLIPSIS
        DiffResult(only_hal (0)=..., only_ldb (1)=...)
        >>> isinstance(diff.only_a, list) and isinstance(diff.only_b, list)
        True
        """
        pubs_a = self._fetch_pubs(a)
        pubs_b = self._fetch_pubs(b)
        keys_a = set(pubs_a)
        keys_b = set(pubs_b)
        merged = regroup_publications({**pubs_a, **pubs_b})
        only_a, only_b = [], []
        for pub in merged.values():
            source_keys = {s.key for s in pub.sources}
            if source_keys <= keys_a and not (source_keys & keys_b):
                only_a.append(pub)
            elif source_keys <= keys_b and not (source_keys & keys_a):
                only_b.append(pub)
        label_a = self._label(a)
        label_b = self._label(b)
        return DiffResult(label_a=label_a, label_b=label_b, only_a=only_a, only_b=only_b)

    def find_duplicates(self, a):
        """
        Find duplicate publications within a single source.

        Parameters
        ----------
        a : :class:`int` or :class:`str`
            Source: index in ``self.sources`` or db_name to match.

        Returns
        -------
        :class:`~gismap.sources.multi.DuplicateResult`
            Groups of publications that appear to be duplicates.

        Examples
        --------

        >>> from gismap.lab import LabAuthor
        >>> me = LabAuthor("Fabien Mathieu (hal:fabien-mathieu, ldb:66/2077)")
        >>> dups = me.find_duplicates("hal")  # doctest: +ELLIPSIS
        >>> dups  # doctest: +ELLIPSIS
        DuplicateResult(hal, ... groups)
        """
        pubs = self._fetch_pubs(a)
        merged = regroup_publications(pubs)
        groups = [sp.sources for sp in merged.values() if len(sp.sources) > 1]
        label = self._label(a)
        return DuplicateResult(label=label, groups=groups)

    def get_publications(self, clean=True, selector=None):
        if selector is None:
            selector = []
        if not isinstance(selector, list):
            selector = [selector]
        res = {p.key: p for a in self.sources for p in a.get_publications() if all(f(p) for f in selector)}
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
    scores = [v.get(getattr(source, k, None), 0) for k, v in publication_score_rosetta.items()]
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

    @property
    def url(self):
        for s in self.sources:
            url = getattr(s, "url", None)
            if url:
                return url
        return None

    @classmethod
    def from_sources(cls, sources):
        sources = sort_publication_sources(sources)
        main = sources[0]
        res = cls(
            **{k: getattr(main, k) for k in ["title", "authors", "venue", "type", "year"]},
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
    redirection = {k: a for a in auth_dict.values() for s in a.sources for k in [s.key, s.name, *s.aliases]}

    for pub in pub_dict.values():
        pub.authors = [redirection.get(a.key, redirection.get(a.name, a)) for a in pub.authors]


def regroup_publications(pub_dict, threshold=83, length_impact=0.05, n_range=5):
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

    Examples
    --------

    >>> from gismap.sources.models import Publication
    >>> from gismap.sources.hal import HALPublication
    >>> from gismap.sources.ldb import LDBPublication
    >>> publis = [HALPublication("The coolest paper", [], "WWW", "conference", 2004, "key1"),
    ... HALPublication("The coolest paper?", [], "WWW journal", "journal", 2004, "key2"),
    ... HALPublication("The coolest paper!", [], "unpublished", "report", 2003, "key3"),
    ... LDBPublication(title="The hottest paper", authors=[], venue="J. WWW", type="journal", year=2004, key="key4"),
    ... LDBPublication(title="The hottest paper?", authors=[], venue="CoRR", type="journal", year=2003, key="key5"),
    ... Publication("The hottest paper!", [], "informal", "zoom meeting", 2002)]
    >>> publis[-1].key = "key6"
    >>> regroup_publications({p.key: p for p in publis})  # doctest: +NORMALIZE_WHITESPACE
    {'key2': SourcedPublication(title='The coolest paper?', venue='WWW journal', type='journal', year=2004),
    'key4': SourcedPublication(title='The hottest paper', venue='J. WWW', type='journal', year=2004)}
    >>> regroup_publications({})  # should not fail on empty input
    {}
    """
    if len(pub_dict) == 0:
        return dict()
    pub_list = [p for p in pub_dict.values()]
    res = dict()
    jc = similarity_matrix(pub_list, key=lambda p: p.fingerprint, n_range=n_range, length_impact=length_impact)
    done = np.zeros(len(pub_list), dtype=bool)
    for i in range(len(pub_list)):
        if done[i]:
            continue
        locs = np.where((jc[i, :] > threshold) & ~done)[0]
        pub = SourcedPublication.from_sources([pub_list[i] for i in locs])
        res[pub.key] = pub
        done[locs] = True
    return res


@dataclass
class DiffResult:
    """Result of comparing publications between two sources."""

    label_a: str
    label_b: str
    only_a: list
    only_b: list

    def __str__(self):
        lines = []
        for label, pubs in [(self.label_a, self.only_a), (self.label_b, self.only_b)]:
            lines.append(f"=== Only in {label} ({len(pubs)}) ===")
            for pub in pubs:
                lines.append(pub.short_str())
        return "\n".join(lines)

    def __repr__(self):
        return f"DiffResult(only_{self.label_a}={len(self.only_a)}, only_{self.label_b}={len(self.only_b)})"


@dataclass
class DuplicateResult:
    """Result of finding duplicate publications within a source."""

    label: str
    groups: list

    def __str__(self):
        lines = [f"=== Duplicates in {self.label} ({len(self.groups)} groups) ==="]
        for i, group in enumerate(self.groups, 1):
            lines.append(f"  Group {i}:")
            for pub in group:
                lines.append(f"  {pub.short_str()}")
        return "\n".join(lines)

    def __repr__(self):
        return f"DuplicateResult({self.label}, {len(self.groups)} groups)"
