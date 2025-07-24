from gismo import MixInIO
from dataclasses import dataclass, field

from gismap.utils.common import LazyRepr
from gismap.utils.logger import logger
from gismap.sources.multi import SourcedAuthor
from gismap.sources.multi import regroup_authors, regroup_publications
from gismap.sources.hal import HAL
from gismap.sources.dblp import DBLP


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
        if dbs is None:
            dbs = [HAL, DBLP]
        sources = []
        for db in dbs:
            source = db.search_author(self.name)
            if len(source) == 0:
                logger.warning(f"{self.name} not found in {db.db_name}")
            elif len(source) > 1:
                logger.warning(f"Multiple entries for {self.name} in {db.db_name}")
            sources += source
        if len(sources) > 0:
            self.sources = sources


class Lab(MixInIO):
    """
    Abstract class for labs.

    Labs can be saved with the `dump` method and loaded with the `load` method.

    Parameters
    ----------
    name: :class:`str`
        Name of the lab. Can be set as class or instance attribute.
    dbs: :class:`list`, default=[:class:`~gismap.sources.hal.HAL`, :class:`~gismap.sources.dblp.DBLP`]
        List of DB sources to use.
    """

    name = None
    dbs = [HAL, DBLP]

    def __init__(self, name=None, dbs=None):
        if name is not None:
            self.name = name
        if dbs is not None:
            self.dbs = dbs
        self.authors = None
        self.publications = None

    def __repr__(self):
        return f"Lab {self.name}"

    def _author_iterator(self):
        """
        Yields
        ------
        :class:`~gismap.lab.lab.LabAuthor`
        """
        raise NotImplementedError

    def update_authors(self):
        """
        Populate the authors attribute (:class:`dict` [:class:`str`, :class:`~gismap.lab.lab.LabAuthor`]).

        Returns
        -------
        None
        """
        self.authors = dict()
        for author in self._author_iterator():
            author.auto_sources(dbs=self.dbs)
            if author.sources:
                self.authors[author.key] = author

    def update_publis(self):
        """
        Populate the publications attribute (:class:`dict` [:class:`str`, :class:`~gismap.sources.multi.SourcedPublication`]).

        Returns
        -------
        None
        """
        pubs = dict()
        for author in self.authors.values():
            pubs.update(author.get_publications(clean=False))
        regroup_authors(self.authors, pubs)
        self.publications = regroup_publications(pubs)


class ListLab(Lab):
    """
    Simplest way to create a lab: with a list of names.

    Parameters
    ----------
    author_list: :class:`list` of :class:`str`
        List of authors names.
    args: :class:`list`
        Arguments to pass to the :class:`~gismap.lab.lab.Lab` constuctor.
    kwargs: :class:`dict`
        Keyword arguments to pass to the :class:`~gismap.lab.lab.Lab` constuctor.
    """

    def __init__(self, author_list, *args, **kwargs):
        self.author_list = author_list
        super().__init__(*args, **kwargs)

    def _author_iterator(self):
        for name in self.author_list:
            yield LabAuthor(name=name, metadata=AuthorMetadata())
