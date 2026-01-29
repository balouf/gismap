from dataclasses import dataclass, field
import re

from gismap import get_classes
from gismap.sources.models import DB, db_class_to_auth_class
from gismap.sources.multi import SourcedAuthor, sort_author_sources
from gismap.utils.common import LazyRepr, list_of_objects
from gismap.utils.logger import logger

db_dict = get_classes(DB, key="db_name")
default_dbs = ["hal", "ldb"]


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
    """
    Examples
    ---------
    The metadata and DB key(s) of an author can be entered in parentheses using key/values.

    Improper key/values are ignored (with a warning).

    >>> dummy= LabAuthor("My Name(img: https://my.url.img, group:me,url:https://mysite.org,hal:key1,ldb:toto,badkey:hello,no_colon_separator)")
    >>> dummy.metadata
    AuthorMetadata(url='https://mysite.org', img='https://my.url.img', group='me')
    >>> dummy.sources
    [HALAuthor(name='My Name', key='key1'), LDBAuthor(name='My Name', key='toto')]

    You can enter multiple keys for the same DB. HAL key types are automatically detected.

    >>> dummy2= LabAuthor("My Name (hal:key1,hal:123456,hal: My Other Name )")
    >>> dummy2.sources
    [HALAuthor(name='My Name', key='key1'), HALAuthor(name='My Name', key='123456', key_type='pid'), HALAuthor(name='My Name', key='My Other Name', key_type='fullname')]
    """

    metadata: AuthorMetadata = field(default_factory=AuthorMetadata)

    def auto_img(self):
        for source in self.sources:
            img = getattr(source, "img", None)
            if img is not None:
                self.metadata.img = img
                break

    def __post_init__(self):
        pattern = r"\s*([^,(]+)\s*(?:\(([^)]*)\))?\s*$"
        match = re.match(pattern, self.name)
        if match:
            self.name = match.group(1).strip()
            content = match.group(2)
            if content:
                for kv in content.split(","):
                    if ":" not in kv:
                        logger.warning(f"I don't know what to do with {kv}.")
                        continue
                    k, v = kv.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k in db_dict:
                        DBAuthor = db_class_to_auth_class(db_dict[k])
                        self.sources.append(DBAuthor(name=self.name, key=v))
                    elif k in ["url", "img", "group"]:
                        setattr(self.metadata, k, v)
                    else:
                        logger.warning(f"I don't know what to do with {kv}.")
        else:
            self.name = self.name.strip()

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
                logger.info(f"{self.name} not found in {db.db_name}")
            elif len(source) > 1:
                logger.info(f"Multiple entries for {self.name} in {db.db_name}")
            sources += source
        if len(sources) > 0:
            self.sources = sort_author_sources(sources)


def labify_author(author, rosetta):
    """
    Convert a database author to a LabAuthor if possible.

    Parameters
    ----------
    author : :class:`~gismap.sources.models.Author`
        Author to convert.
    rosetta : :class:`dict`
        Mapping from keys/names to LabAuthor objects.

    Returns
    -------
    :class:`~gismap.lab.lab_author.LabAuthor` or original author
        LabAuthor if found in rosetta, otherwise the original author.
    """
    if isinstance(author, LabAuthor):
        return author
    return rosetta.get(author.key, rosetta.get(author.name, author))


def labify_publications(pubs, rosetta):
    """
    Convert publication authors to LabAuthors in place.

    Parameters
    ----------
    pubs : :class:`list`
        Publications to update.
    rosetta : :class:`dict`
        Mapping from keys/names to LabAuthor objects.

    Returns
    -------
    None
    """
    for pub in pubs:
        pub.authors = [labify_author(a, rosetta) for a in pub.authors]
        for source in getattr(pub, "sources", []):
            source.authors = [labify_author(a, rosetta) for a in pub.authors]
