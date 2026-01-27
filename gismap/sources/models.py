from dataclasses import dataclass
from typing import ClassVar

from gismap.utils.common import LazyRepr


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
    """
    for subclass in Author.__subclasses__():
        if db_class in subclass.__mro__:
            return subclass
    return None
