from gismap.lab.lab_author import LabAuthor
from gismap.lab.labmap import LabMap

# Effectively "no cap": larger than any realistic prospect pool. Used by
# build(target=None) to take every planet without a magic sentinel in expand().
_UNLIMITED = 10**9


class EgoMap(LabMap):
    """
    Egocentric view of a researcher's collaboration network.

    Displays the *star* (central researcher), their *planets* (direct co-authors),
    and optionally *moons* (co-authors of co-authors).

    Parameters
    ----------
    star: :class:`str` or :class:`~gismap.lab.lab_author.LabAuthor`
        The central researcher. Can be a name string or LabAuthor object.
    *args
        Passed to :class:`~gismap.lab.labmap.LabMap`.
    **kwargs
        Passed to :class:`~gismap.lab.labmap.LabMap`.

    Examples
    --------

    >>> dang = EgoMap("The-Dang Huynh")
    >>> dang.build(target=20)
    >>> sorted(  # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
    ...     a.name for a in dang.authors.values() if len(a.name.split()) < 3
    ... )
    ['Bruno Kauffmann', 'Diego Perino', 'Dohy Hong', 'Fabien Mathieu', 'François Baccelli',...]

    To add publications, one can use the :meth:`~gismap.lab.labmap.LabMap.add_publication` method:

    >>> dang.add_publication(
    ...     title="A new paper",
    ...     authors=[dang.star, "Fabien Mathieu", "Alice Smith"],
    ...     venue="Journal of Testing",
    ... )
    >>> str(dang.select_publications(lambda p: "Testing" in p.venue)[0])
    'A new paper, by The-Dang Huynh, Fabien Mathieu, and Alice Smith. In Journal of Testing [unpublished], 2026.'

    To remove publications, one can use the :meth:`~gismap.lab.labmap.LabMap.del_publication` method:

    >>> dang.del_publication("A new paper", confirm=False)
    >>> dang.select_publications(lambda p: "Testing" in p.venue)
    []

    """

    def __init__(self, star, *args, **kwargs):
        if isinstance(star, str):
            star = LabAuthor(star)
        star.metadata.position = (0, 0)
        star.metadata.group = "star"
        self.star = star
        super().__init__(*args, **kwargs)
        if self.name is None:
            self.name = star.name

    def _author_iterator(self):
        yield self.star

    def __repr__(self):
        return f"EgoMap('{self.name}')"

    def __str__(self):
        n_auth = len(self.authors) if self.authors else "?"
        n_pub = len(self.publications) if self.publications else "?"
        return f"EgoMap of {self.name} ({n_auth} authors, {n_pub} publications)"

    def build(self, target=50, moon_ratio=0.5, **kwargs):
        """
        Build the ego network by fetching publications and adding planets/moons.

        Parameters
        ----------
        target : :class:`int` or None, default=50
            Target number of authors in the final map. Use ``None`` for an
            *exhaustive* map: every planet (direct co-author) is kept, then
            moons are capped at ``moon_ratio`` times the number of planets
            found. The cap matters because taking *all* moons routinely reaches
            several thousand authors.
        moon_ratio : :class:`float`, default=0.5
            Only used when ``target=None``: number of moons to add, as a
            fraction of the number of planets found.
        **kwargs
            Passed to :meth:`~gismap.lab.labmap.LabMap.expand`.

        Returns
        -------
        None
        """
        self.update_authors(desc="Star metadata")
        self.update_publis(desc="Star publications")
        if target is None:
            n_before = len(self.authors)
            self.expand(group="planet", target=_UNLIMITED, desc="Planets", **kwargs)
            moon_cap = int((len(self.authors) - n_before) * moon_ratio)
            if moon_cap > 0:
                self.expand(group="moon", target=moon_cap, desc="Moons", **kwargs)
        else:
            kwargs["target"] = target - len(self.authors)
            self.expand(group="planet", desc="Planets", **kwargs)
            kwargs["target"] = target - len(self.authors)
            if kwargs["target"] > 0:
                self.expand(group="moon", desc="Moons", **kwargs)
