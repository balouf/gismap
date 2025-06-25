from dataclasses import dataclass, field

from gismap.database.blueprint import DBAuthor


score_rosetta = {
    'origin': {'dblp': 1, 'hal': 2},
    'venue': {'CoRR': -1, 'unpublished': -2},
    'type': {'conference': 1, 'journal': 2}
}
"""
Scoring system to decide the best representative of a publication in case of duplicate.

* Prefer HAL entries over DBLP entries
* Arxiv entries are deprecated, unpublished even more
* Prefer journal version over conference version
* Implemented in the actual function: use year as final tie-breaker.
"""


@dataclass
class Publication:
    """
    Parameters
    ----------
    raw_list: :class:`list`
        Raw sources of the publication. All entries are supposed to refer to the same actual publication.
    """
    key: str
    """Unique identifier of publication."""
    title: str
    """Title of publication."""
    authors: list[DBAuthor]
    """List of authors."""
    venue: str
    """Venue (name of conference/journal)"""
    year: int
    """Year of publication."""
    abstract: str = field(repr=False)
    """Abstract of publication (optional)."""
    sources: dict = field(repr=False)
    """Raw dictionaries of publication (one unique dictionary per DB, design choice)."""
    type: str = field(repr=False)
    """Type of publication (conference, poster, journal, ...)."""

    def __init__(self, raw_list):
        raw_list = sorted(raw_list, key=lambda p: self.score_raw_publi(p), reverse=True)

        for attr in ['key', 'title', 'authors', 'venue', 'year', 'type']:
            setattr(self, attr, raw_list[0][attr])

        self.sources = dict()
        self.abstract = None
        for p in raw_list:
            if self.abstract is None and p.get('abstract'):
                self.abstract = p['abstract']
            origin = p['origin']
            if origin not in self.sources:
                self.sources[origin] = p

    @staticmethod
    def score_raw_publi(paper):
        """
        Parameters
        ----------
        paper: :class:`dict`
            Raw publication entry (must have at least the keys `origin`, `venue`, `type`, `year`).

        Returns
        -------
        :class:`tuple`
            Score to sort the publication.
        """
        scores = [v.get(paper[k], 0) for k, v in score_rosetta.items()]
        scores.append(paper['year'])
        return tuple(scores)

    @property
    def string(self):
        """
        :class:`str`
            Textual description, as in a bibliography.
        """
        return f"{self.title}, by {', '.join(a.name for a in self.authors)}. {self.venue}, {self.year}."
