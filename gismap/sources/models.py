from dataclasses import dataclass
from typing import ClassVar

from gismap.utils.common import LazyRepr
from gismap.utils.text import normalized_name, normalized_title


@dataclass(repr=False)
class Author(LazyRepr):
    """
    Base class for authors in the database system.

    Authors are identified primarily by their name and may have
    database-specific subclasses with additional attributes like keys and aliases.

    Parameters
    ----------
    name : :class:`str`
        The author's name.
    """

    name: str

    @property
    def fingerprint(self):
        """
        A normalized version of the author's name for matching purposes.

        Returns
        -------
        :class:`str`
            The fingerprint of the author's name.
        """
        return normalized_name(self.name)

    def __str__(self):
        return self.name


def format_authors(authors, transform=None):
    """Format a list of Author objects into a human-readable string.

    Parameters
    ----------
    authors : :class:`list`
        List of Author objects.
    transform : :class:`callable`, optional
        A function to apply to each Author for display purposes (e.g., extracting a name).
         If None, the default string representation of Author is used.

    Returns
        -------
        :class:`str`
            A human-readable string representing the formatted authors.
    """
    if transform is None:
        transform = str

    if not authors:
        return ""
    if len(authors) == 1:
        return transform(authors[0])
    if len(authors) == 2:
        return f"{transform(authors[0])} and {transform(authors[1])}"
    return ", ".join(transform(author) for author in authors[:-1]) + ", and " + transform(authors[-1])


@dataclass(repr=False)
class Publication(LazyRepr):
    """
    Base class for publications in the database system.

    Publications contain metadata about academic papers including title,
    authors, venue, type, and publication year.

    Parameters
    ----------
    title : :class:`str`
        The publication title.
    authors : :class:`list`
        List of :class:`Author` objects.
    venue : :class:`str`
        Publication venue (journal, conference, etc.).
    type : :class:`str`
        Publication type (e.g., 'journal', 'conference', 'book').
    year : :class:`int`
        Year of publication.
    """

    title: str
    authors: list
    venue: str
    type: str
    year: int

    @property
    def fingerprint(self):
        """
        A normalized version of the publication's title for matching purposes.

        Returns
        -------
        :class:`str`
            The fingerprint of the publication's title.

        Examples
        --------
        >>> pub = Publication(title="A Studÿ: on Foo!!",
        ... authors=[Author(name="John Döe"), Author(name="Jáne Smith")], venue="", type="", year=2020)
        >>> pub.fingerprint
        'a study on foo---doe john+++jane smith'
        """
        return normalized_title(self.title) + "---" + "+++".join(a.fingerprint for a in self.authors)

    def __str__(self):
        title = self.title
        if title.endswith("."):
            title = title[:-1]
        return f"{title}, by {format_authors(self.authors)}. In {self.venue} [{self.type}], {self.year}."


@dataclass(repr=False)
class DB(LazyRepr):
    """
    Abstract base class for database backends.

    Provides the interface for searching authors and retrieving publications.
    Subclasses must implement :meth:`search_author` and :meth:`from_author`.

    Attributes
    ----------
    db_name : :class:`str`
        Identifier for the database backend (e.g., 'hal', 'dblp', 'ldb').
    """

    db_name: ClassVar[str] = None

    @classmethod
    def search_author(cls, name):
        """
        Search for authors matching the given name.

        Parameters
        ----------
        name : :class:`str`
            Name to search for.

        Returns
        -------
        :class:`list`
            List of matching :class:`Author` objects.
        """
        raise NotImplementedError

    @classmethod
    def from_author(cls, a):
        """
        Retrieve publications for a given author.

        Parameters
        ----------
        a : :class:`Author`
            The author whose publications to retrieve.

        Returns
        -------
        :class:`list`
            List of :class:`Publication` objects.
        """
        raise NotImplementedError


def db_class_to_auth_class(db_class):
    """
    Find the Author subclass associated with a given DB class.

    Parameters
    ----------
    db_class : :class:`type`
        A DB subclass (e.g., HAL, DBLP, LDB).

    Returns
    -------
    :class:`type` or None
        The corresponding Author subclass, or None if not found.

    Examples
    --------
    >>> from gismap.sources.hal import HAL
    >>> db_class_to_auth_class(HAL)
    <class 'gismap.sources.hal.HALAuthor'>
    >>> class Alien: pass
    >>> db_class_to_auth_class(Alien)
    """
    for subclass in Author.__subclasses__():
        if db_class in subclass.__mro__:
            return subclass
    return None
