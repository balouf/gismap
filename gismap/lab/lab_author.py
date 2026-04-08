import re
from dataclasses import dataclass, field

from gismap.sources.models import DB, db_class_to_auth_class
from gismap.sources.multi import SourcedAuthor, sort_author_sources
from gismap.utils.common import LazyRepr, get_classes, list_of_objects
from gismap.utils.logger import logger

default_dbs = ["hal", "ldb"]


def db_dict():
    """Lazy lookup of DB subclasses (avoids import-order dependency).

    Forces import of all known backends so that ``get_classes`` sees them
    even when some are lazily imported at package level.
    """
    from gismap import DBLP, HAL, LDB  # noqa: F401

    return get_classes(DB, key="db_name")


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
    --------
    The metadata and DB key(s) of an author can be entered in parentheses using key/values.

    Improper key/values are ignored (with a warning).

    >>> dummy= LabAuthor("My Name(img: https://my.url.img, group:me,url:https://mysite.org,hal:key1,ldb:toto,badkey:hello,no_colon_separator)")
    >>> dummy.metadata
    AuthorMetadata(url='https://mysite.org', img='https://my.url.img', group='me')
    >>> dummy.sources
    [HALAuthor(name='My Name', key='key1'), LDBAuthor(name='My Name', key='toto')]

    You can enter multiple keys for the same DB. HAL key types are automatically detected.

    >>> dummy2= LabAuthor("My Name (hal:key1,hal:123456,hal: My Other Name )")
    >>> dummy2.sources  # doctest: +NORMALIZE_WHITESPACE
    [HALAuthor(name='My Name', key='key1'),
    HALAuthor(name='My Name', key='123456', key_type='pid'),
    HALAuthor(name='My Name', key='My Other Name', key_type='fullname')]

    For HAL, ``hal:fullname`` is a shorthand to force a fullname search
    using the author's name (useful when the pid is too restrictive).

    >>> dummy3 = LabAuthor("Élie de Panafieu (hal:fullname)")
    >>> dummy3.sources
    [HALAuthor(name='Élie de Panafieu', key='Élie de Panafieu', key_type='fullname')]

    By default, :meth:`auto_sources` completes missing DBs automatically.
    Use the ``no_auto`` flag to disable this and keep only the explicit sources
    (e.g. to avoid homonyme pollution from other databases).

    >>> dummy4 = LabAuthor("John Smith (hal:fullname, no_auto)")
    >>> dummy4.no_auto
    True
    """

    metadata: AuthorMetadata = field(default_factory=AuthorMetadata)
    no_auto: bool = False

    @property
    def fingerprint(self):
        return self.key if self.key is not None else super().fingerprint

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
                        flag = kv.strip().lower()
                        if flag == "no_auto":
                            self.no_auto = True
                        else:
                            logger.warning(f"I don't know what to do with {kv}.")
                        continue
                    k, v = kv.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k in db_dict():
                        DBAuthor = db_class_to_auth_class(db_dict()[k])
                        self.sources.append(DBAuthor(name=self.name, key=v))
                    elif k in ["url", "img", "group"]:
                        setattr(self.metadata, k, v)
                    else:
                        logger.warning(f"I don't know what to do with {kv}.")
        else:
            self.name = self.name.strip()

    def auto_sources(self, dbs=None):
        """
        Automatically search for the author in databases not already represented in sources.

        If the author already has explicit sources (e.g. from parentheses notation),
        only the missing databases are queried. Does nothing if :attr:`no_auto` is True.

        Parameters
        ----------
        dbs: :class:`list`, default=[:class:`~gismap.sources.hal.HAL`, :class:`~gismap.sources.dblp.DBLP`]
            List of DB sources to use.

        Returns
        -------
        None
        """
        if self.no_auto:
            logger.info(f"Automatic source retrieval is disabled for {self.name}.")
            return
        dbs = list_of_objects(dbs, db_dict(), default=default_dbs)
        known_dbs = {s.db_name for s in self.sources}
        sources = []
        for db in dbs:
            if db.db_name in known_dbs:
                continue
            source = db.search_author(self.name)
            if len(source) == 0:
                logger.info(f"{self.name} not found in {db.db_name}")
            elif len(source) > 1:
                logger.info(f"Multiple entries for {self.name} in {db.db_name}")
            sources += source
        if len(sources) > 0:
            self.sources = sort_author_sources(self.sources + sources)
