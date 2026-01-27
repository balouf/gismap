from collections import Counter, defaultdict
from dataclasses import dataclass
from bof.fuzz import Process
import numpy as np

from gismap.utils.text import normalized_name
from gismap.sources.multi import sort_author_sources
from gismap.lab.lab_author import LabAuthor


@dataclass
class ProspectStrength:
    """
    Measures the interaction between an external author and a lab by counting co-authors and publications.

    A (max,+) addition is handled to deal with multiple keys.

    Examples
    --------

    >>> a1 = ProspectStrength(3, 5)
    >>> a2 = ProspectStrength(2, 10)
    >>> a1 > a2
    True
    >>> a1 + a2
    ProspectStrength(coauthors=3, publications=15)
    """

    coauthors: int
    publications: int

    def __call__(self):
        return self.coauthors, self.publications

    def __add__(self, other):
        if other == 0:
            return self
        return ProspectStrength(
            coauthors=max(self.coauthors, other.coauthors),
            publications=self.publications + other.publications,
        )

    def __radd__(self, other):
        return self.__add__(other)

    def __lt__(self, other):
        return self() < other()


def count_prospect_entries(lab):
    """
    Associate to external coauthors (prospects) their lab strength.

    Parameters
    ----------
    lab: :class:`~gismap.lab.labmap.LabMap`
        Reference lab.

    Returns
    -------
    :class:`dict` of :class:`str` to :class:`~gismap.lab.expansion.ProspectStrength`
        Lab strengths.
    """
    count_coauthors = defaultdict(set)
    count_publications = []
    for p in lab.publications.values():
        for s in p.sources:
            new_authors = set()
            lab_authors = set()
            for a in s.authors:
                if hasattr(a, "db_name"):
                    new_authors.add(a.key)
                    count_publications.append(a.key)
                else:
                    lab_authors.add(a.key)
            for a in lab_authors:
                count_coauthors[a].update(new_authors)

    count_coauthors = Counter(
        k for new_authors in count_coauthors.values() for k in new_authors
    )
    count_publications = Counter(count_publications)

    return {
        k: ProspectStrength(
            coauthors=count_coauthors.get(k, 0), publications=count_publications[k]
        )
        for k in count_publications
    }


class Prospect:
    """
    Candidate for integration to lab.

    Parameters
    ----------
    author: :class:`~gismap.sources.models.Author`
        Reference author. Must have a key.
    strengths: :class:`dict`
        Dictionary of ProspectStrength.
    """

    def __init__(self, author, strengths):
        self.name = normalized_name(author.name)
        self.author = author
        self.score = strengths[author.key]

    def __lt__(self, other):
        return self.score < other.score

    def __repr__(self):
        return f"Prospect({self.name}, key={self.author.key}, s={self.score()}"


def get_prospects(lab):
    """
    Parameters
    ----------
    lab: :class:`~gismap.lab.labmap.LabMap`
        Reference lab.

    Returns
    -------
    :class:`list` of :class:`~gismap.lab.expansion.Prospect`
        List of prospects.
    """
    strengths = count_prospect_entries(lab)
    prospect_dico = {
        a.key: a
        for p in lab.publications.values()
        for s in p.sources
        for a in s.authors
        if hasattr(a, "db_name") and all(f(a) for f in lab.author_selectors)
    }
    return [Prospect(a, strengths) for a in prospect_dico.values()]


@dataclass
class Member:
    """
    Basic information about a lab member for name matching.

    Parameters
    ----------
    name : :class:`str`
        Normalized name.
    key : :class:`str`
        Author key.
    """

    name: str
    key: str


def get_member_names(lab):
    """
    Parameters
    ----------
    lab: :class:`~gismap.lab.labmap.LabMap`
        Reference lab.

    Returns
    -------
    :class:`list`
        Tuples simplified-name -> key
    """
    return [
        (name, k)
        for k, a in lab.authors.items()
        for name in {normalized_name(n) for n in [a.name, *a.aliases]}
    ]


def trim_sources(author):
    """
    Inplace reduction of sources, keeping one unique source per db.

    Parameters
    ----------
    author: :class:`~gismap.sources.multi.SourcedAuthor`
        An author.

    Returns
    -------
    None
    """
    sources = []
    seen = set()
    for s in author.sources:
        if s.db_name not in seen:
            seen.add(s.db_name)
            sources.append(s)
    author.sources = sources


def proper_prospects(
    lab, length_impact=0.05, threshold=80, n_range=4, max_new=None, trim=True
):
    """
    Find and rank external collaborators for potential lab expansion.

    Identifies authors from publications who are not already lab members,
    groups them by name similarity, and ranks by collaboration strength.

    Parameters
    ----------
    lab : :class:`~gismap.lab.labmap.LabMap`
        Reference lab.
    length_impact : :class:`float`, default=0.05
        Length impact for name similarity matching.
    threshold : :class:`int`, default=80
        Similarity threshold for grouping authors.
    n_range : :class:`int`, default=4
        N-gram range for name comparison.
    max_new : :class:`int`, optional
        Maximum number of new authors to return.
    trim : :class:`bool`, default=True
        If True, keep only one source per database for each author.

    Returns
    -------
    :class:`tuple`
        (existing, new_rosetta) where existing maps external keys to lab member keys,
        and new_rosetta maps source keys to new LabAuthor objects.
    """
    member_names = get_member_names(lab)
    prospects = get_prospects(lab)

    if len(member_names) == 0 or len(prospects) == 0:
        return dict(), dict()

    done = np.zeros(len(prospects), dtype=bool)

    # Compare current and prospects names to re-attach ghosts
    p = Process(length_impact=length_impact, n_range=n_range)
    p.allow_updates = False
    p.fit([n[0] for n in member_names])
    jc = p.transform([prospect.name for prospect in prospects])
    best_choice = np.argmax(jc, axis=1)
    existing = dict()
    for i, j in enumerate(best_choice):
        if jc[i, j] > threshold:
            existing[prospects[i].author.key] = member_names[j][1]
            done[i] = True

    # Regroup remaining prospects
    p.reset()
    names = [prospect.name for prospect in prospects]
    p.fit(names)
    jc = p.transform(names)
    new_lab = []
    for i, prospect in enumerate(prospects):
        if done[i]:
            continue
        locs = [j for j in np.where(jc[i, :] > threshold)[0] if not done[j]]
        done[locs] = True
        sources = sort_author_sources([prospects[j].author for j in locs])
        if sources:
            strength = sum(prospects[j].score for j in locs)
            new_author = LabAuthor.from_sources(sources)
            new_lab.append((strength, new_author))

    # Extract top prospects
    new_lab = [a[1] for a in sorted(new_lab, key=lambda a: a[0], reverse=True)][
        :max_new
    ]
    new_rosetta = {s.key: a for a in new_lab for s in a.sources}

    # Remove extra sources
    if trim:
        for a in new_lab:
            trim_sources(a)

    return existing, new_rosetta
