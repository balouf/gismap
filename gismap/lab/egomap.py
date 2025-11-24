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
        target = kwargs.pop("target", 50)
        self.update_authors(desc="Star metadata")
        self.update_publis(desc="Star publications")
        kwargs["target"] = target - len(self.authors)
        self.expand(group="planet", desc="Planets", **kwargs)
        kwargs["target"] = target - len(self.authors)
        if kwargs["target"] > 0:
            self.expand(group="moon", desc="Moons", **kwargs)
