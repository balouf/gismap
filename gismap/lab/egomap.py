from gismap.lab.lab import Lab
from gismap.lab.lab_author import LabAuthor


class EgoMap(Lab):
    def __init__(self, sun, *args, **kwargs):
        if isinstance(sun, str):
            sun = LabAuthor(sun)
        sun.metadata.position = (0, 0)
        self.sun = sun
        super().__init__(*args, **kwargs)

    def _author_iterator(self):
        yield self.sun

    def build(self, **kwargs):
        target = kwargs.pop("target", 50)
        group = kwargs.pop("group", "moon")
        self.update_authors(desc="Sun metadata")
        self.update_publis(desc="Sun publications")
        kwargs["target"] = target - len(self.authors)
        self.expand(group=None, desc="Planets", **kwargs)
        kwargs.update({"target": target - len(self.authors), "group": group})
        if kwargs["target"] > 0:
            self.expand(desc="Moons", **kwargs)
