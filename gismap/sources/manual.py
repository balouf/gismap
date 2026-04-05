"""Manual data source for hand-crafted publications and external authors."""

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import ClassVar

import numpy as np

from gismap.sources.models import DB, Author, Publication
from gismap.utils.fuzzy import similarity_matrix
from gismap.utils.text import normalized_name


@dataclass(repr=False)
class Manual(DB):
    """Dummy database backend for manually created entries."""

    db_name: ClassVar[str] = "manual"

    @classmethod
    def search_author(cls, name):
        return []

    @classmethod
    def from_author(cls, a):
        return []


@dataclass(repr=False)
class Outsider(Author, Manual):
    """
    An external author not found in any database.

    Used when manually adding publications with authors that don't exist
    in HAL, DBLP, or LDB.

    Parameters
    ----------
    name: :class:`str`
        Author name.
    key: :class:`str`, optional
        Author key. Defaults to normalized name.
    aliases: :class:`list`
        Known name variants.
    """

    key: str = None
    aliases: list = field(default_factory=list)

    def __post_init__(self):
        if self.key is None:
            self.key = normalized_name(self.name)

    def get_publications(self):
        return []


@dataclass(repr=False)
class Informal(Publication, Manual):
    """
    A manually created publication not from any database.

    Parameters
    ----------
    title: :class:`str`
        Publication title.
    authors: :class:`list`
        List of author objects or name strings.
    venue: :class:`str`, default="Informal collaboration"
        Publication venue.
    type: :class:`str`, default="unpublished"
        Publication type.
    year: :class:`int`, optional
        Publication year. Defaults to current year.
    key: :class:`str`, optional
        Unique key. Auto-generated if not provided.
    metadata: :class:`dict`
        Extra metadata (e.g. ``{"url": "..."}``).
    """

    year: int = date.today().year
    type: str = "unpublished"
    venue: str = "Informal collaboration"
    key: str = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.key is None:
            self.key = uuid.uuid4().hex

    @property
    def url(self):
        """Publication URL from metadata, if available."""
        return self.metadata.get("url")

    def fit_authors(self, lab, **kwargs):
        """Resolve string author names to known lab/database authors in place."""
        fit_names(lab, self.authors, **kwargs)


def fit_names(lab, candidates, n_range=4, length_impact=0.05, threshold=80):
    """
    Resolve string names in a candidate list to known authors from a lab's publications.

    Each string entry in ``candidates`` is compared against all known authors
    (from the lab's publications). If a match is found above ``threshold``,
    the string is replaced in place by the matching author object. Otherwise,
    it is replaced by an :class:`Outsider`.

    Parameters
    ----------
    lab : :class:`~gismap.lab.labmap.LabMap`
        Reference lab (must have publications populated).
    candidates : :class:`list`
        List of authors (strings or author objects). Modified in place.
    n_range : :class:`int`, default=4
        N-gram range for similarity computation.
    length_impact : :class:`float`, default=0.05
        Impact of length difference on similarity scores.
    threshold : :class:`float`, default=80
        Minimum similarity score to accept a match.
    """
    known_dict = {
        a.key: a
        for p in lab.publications.values()
        for s in p.sources
        for a in s.authors
        if all(f(a) for f in lab.author_selectors)
    }
    raw_candidates = [(normalized_name(c), i) for i, c in enumerate(candidates) if isinstance(c, str)]
    if not raw_candidates:
        return
    options = [(n, a) for a in known_dict.values() for n in {normalized_name(nn) for nn in [a.name, *a.aliases]}]
    jc = similarity_matrix(
        options,
        candidates=raw_candidates,
        key=lambda x: x[0],
        key2=lambda x: x[0],
        n_range=n_range,
        length_impact=length_impact,
    )
    for i, j in enumerate(np.argmax(jc, axis=1)):
        _, pos = raw_candidates[i]
        if jc[i, j] > threshold:
            candidates[pos] = options[j][1]
        else:
            candidates[pos] = Outsider(name=candidates[pos])
