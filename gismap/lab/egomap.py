from gismap.lab.labmap import LabMap
from gismap.lab.lab_author import LabAuthor


class EgoMap(LabMap):
    """
    Parameters
    ----------
    star
    args
    kwargs

    Examples
    --------

    >>> dang = EgoMap("The-Dang Huynh", dbs="hal")
    >>> dang.build(target=10)
    >>> sorted(a.name for a in dang.authors.values())  # doctest: +NORMALIZE_WHITESPACE
    ['Bruno Kauffmann', 'Chung Shue Chen', 'Fabien Mathieu', 'François Baccelli', 'Laurent Viennot', 'Ludovic Noirie',
    'Siu-Wai Ho', 'Sébastien Tixeuil', 'The-Dang Huynh', 'Yannick Carlinet']
    """

    def __init__(self, star, *args, **kwargs):
        if isinstance(star, str):
            star = LabAuthor(star)
        star.metadata.position = (0, 0)
        self.star = star
        super().__init__(*args, **kwargs)

    def _author_iterator(self):
        yield self.star

    def build(self, **kwargs):
        target = kwargs.pop("target", 50)
        group = kwargs.pop("group", "moon")
        self.update_authors(desc="Star metadata")
        self.update_publis(desc="Star publications")
        kwargs["target"] = target - len(self.authors)
        self.expand(group=None, desc="Planets", **kwargs)
        kwargs.update({"target": target - len(self.authors), "group": group})
        if kwargs["target"] > 0:
            self.expand(desc="Moons", **kwargs)
