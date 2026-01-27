from gismap.lab.labmap import LabMap
from gismap.lab.lab_author import LabAuthor


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

    >>> dang = EgoMap("The-Dang Huynh", dbs="hal")
    >>> dang.build(target=10)
    >>> sorted(a.name for a in dang.authors.values())  # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
    ['Bruno Kauffmann', 'Chung Shue Chen', 'Fabien Mathieu',...
    """

    def __init__(self, star, *args, **kwargs):
        if isinstance(star, str):
            star = LabAuthor(star)
        star.metadata.position = (0, 0)
        star.metadata.group = "star"
        self.star = star
        super().__init__(*args, **kwargs)

    def _author_iterator(self):
        yield self.star

    def build(self, **kwargs):
        """
        Build the ego network by fetching publications and adding planets/moons.

        Parameters
        ----------
        target : :class:`int`, default=50
            Target number of authors in the final map.
        **kwargs
            Passed to :meth:`~gismap.lab.labmap.LabMap.expand`.

        Returns
        -------
        None
        """
        target = kwargs.pop("target", 50)
        self.update_authors(desc="Star metadata")
        self.update_publis(desc="Star publications")
        kwargs["target"] = target - len(self.authors)
        self.expand(group="planet", desc="Planets", **kwargs)
        kwargs["target"] = target - len(self.authors)
        if kwargs["target"] > 0:
            self.expand(group="moon", desc="Moons", **kwargs)
