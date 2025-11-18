from dataclasses import dataclass, field

from gismap import get_classes, HAL, DBLP
from gismap.sources.models import DB
from gismap.sources.multi import SourcedAuthor, sort_author_sources
from gismap.utils.common import LazyRepr, list_of_objects
from gismap.utils.logger import logger

db_dict = get_classes(DB, key="db_name")
default_dbs = [HAL, DBLP]


@dataclass(repr=False)
class AuthorMetadata(LazyRepr):
    """
    Optional information about an author to be used to enhance her presentation.

    Attributes
    ----------

    url: :class:`str`
        Homepage of the author.
    img: :class:`str`
        Url to a picture.
    group: :class:`str`
        Group of the author.
    position: :class:`tuple`
        Coordinates of the author.
    """

    url: str = None
    img: str = None
    group: str = None
    position: tuple = None


@dataclass(repr=False)
class LabAuthor(SourcedAuthor):
    metadata: AuthorMetadata = field(default_factory=AuthorMetadata)

    def auto_img(self):
        for source in self.sources:
            img = getattr(source, "img", None)
            if img is not None:
                self.metadata.img = img
                break

    def auto_sources(self, dbs=None):
        """
        Automatically populate the sources based on author's name.

        Parameters
        ----------
        dbs: :class:`list`, default=[:class:`~gismap.sources.hal.HAL`, :class:`~gismap.sources.dblp.DBLP`]
            List of DB sources to use.

        Returns
        -------
        None
        """
        dbs = list_of_objects(dbs, db_dict, default=default_dbs)
        sources = []
        for db in dbs:
            source = db.search_author(self.name)
            if len(source) == 0:
                logger.warning(f"{self.name} not found in {db.db_name}")
            elif len(source) > 1:
                logger.warning(f"Multiple entries for {self.name} in {db.db_name}")
            sources += source
        if len(sources) > 0:
            self.sources = sort_author_sources(sources)


def labify_author(author, rosetta):
    if isinstance(author, LabAuthor):
        return author
    return rosetta.get(author.key, rosetta.get(author.name, author))


def labify_publications(pubs, rosetta):
    for pub in pubs:
        pub.authors = [labify_author(a, rosetta) for a in pub.authors]
        for source in getattr(pub, "sources", []):
            source.authors = [labify_author(a, rosetta) for a in pub.authors]
