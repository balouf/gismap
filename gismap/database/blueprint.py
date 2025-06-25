from dataclasses import dataclass, field, asdict
from typing import ClassVar

from gismap.utils.common import LazyRepr
from gismap.utils.logger import logger


@dataclass(repr=False)
class DBAuthor(LazyRepr):
    """
    Blueprint for DB-specific author management.
    """
    db_name: ClassVar[str] = None
    """Name of the database."""
    query_id_backoff: ClassVar[float] = 0.0
    """Time to wait between 2 *query id* calls."""
    query_publications_backoff: ClassVar[float] = 0.0
    """Time to wait between 2 *query publications* calls."""

    name: str
    """Author name."""
    id: str = None
    """Id of author in DB."""
    aliases: list = field(default_factory=list)
    """Alternative names for the author."""

    def query_publications(self, s=None):
        """
        Parameters
        ----------
        s: :class:`~requests.Session`, optional
            Session.

        Returns
        -------
        :class:`list`
            Papers available in DB.
        """
        raise NotImplementedError

    def update_values(self, author):
        """
        Parameters
        ----------
        author: :class:`~gismap.database.blueprint.DBAuthor`
            External author info to inject in current instance.

        Returns
        -------
        None
        """
        self.id = author.id
        self.aliases = author.aliases

    def query_id(self, s=None):
        """
        Parameters
        ----------
        s: :class:`~requests.Session`, optional
            Session.

        Returns
        -------
        :class:`list`
            Potential matches.
        """
        raise NotImplementedError

    def populate_id(self, s=None):
        """
        Try to automatically fill-in DB information.
        If one unique match is found, the data is integrated.

        Otherwise, a warning is issued, with some suggestions/URLS.

        Parameters
        ----------
        s: :class:`~requests.Session`, optional
            Session.

        Returns
        -------
        :class:`int`
            Number of matches found (i.e. 1 means success).
        """
        matches = self.query_id(s)
        size = len(matches)
        if size == 1:
            self.update_values(matches[0])
        elif size > 1:
            choices = '\n'.join(f"{i.url} -> {str(i)}" for i in matches)
            logger.warning(
                f"Multiple entries found for {self.name} in {self.db_name}. "
                f"Please populate manually. "
                f"Entries found:\n{choices}")
        else:
            logger.warning(f"No entry found for {self.name} in {self.db_name}. Please populate manually.")
            logger.warning(self.url)
        return size

    @property
    def url(self):
        """
        :class:`str`
            URL associated with the author in the DB.
        """
        raise NotImplementedError

    @property
    def is_set(self):
        """
        :class:`bool`
            Is the author identified in DB?
        """
        return self.id is not None

    def iter_keys(self):
        """
        Yields
        -------
        :class:`str` or :class:`int`
            Key of author (typically name, alias, or internal key).
        """
        for key in asdict(self).values():
            if key:
                if isinstance(key, list):
                    for k in key:
                        yield k
                else:
                    yield key


def clean_aliases(name, alias_list):
    """
    Parameters
    ----------
    name: :class:`str`
        Main name.
    alias_list: :class:`list`
        Aliases.

    Returns
    -------
    :class:`list`
        Aliases deduped, sorted, and with main name removed.
    """
    return sorted(set(n for n in alias_list if n != name))

