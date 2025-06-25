from time import sleep

from gismap.database.blueprint import DBAuthor
from gismap.utils.common import LazyRepr, get_classes
from gismap.utils.logger import logger


class Member(LazyRepr):
    """
    Parameters
    ----------
    name: :class:`str`
        Member name.
    pid: :class:`str`, optional
        Unique id (in case of homonyyms in the lab)
    db_dict: :class:`dict`
        Publication DBs to use. Default to all available.
    """
    def __init__(self, name, pid=None, db_dict=None):
        self.name = name
        self.pid = pid
        if db_dict is None:
            db_dict = get_classes(DBAuthor, key='db_name')
        self.sources = {db: author(name=name) for db, author in db_dict.items()}
        self.publications = []

    @property
    def key(self):
        """
        :class:`str`
            Index key of member.
        """
        return self.pid if self.pid else self.name

    def prepare(self, s=None, backoff=False, rewrite=False):
        """
        Fetch member identifiers in her databases.

        Parameters
        ----------
        s: :class:`~requests.Session`, optional
            A session (may be None).
        backoff: :class:`bool`, default=False
            Wait between queries.
        rewrite: :class:`bool`, default=False
            Update even if identifiers are already set.

        Returns
        -------
        None
        """
        for db_author in self.sources.values():
            if rewrite or not db_author.is_set:
                db_author.populate_id(s)
                if backoff:
                    sleep(db_author.query_id_backoff)

    def get_papers(self, s=None, backoff=False):
        """
        Fetch publications from databases.

        Parameters
        ----------
        s: :class:`~requests.Session`, optional
            A session (may be None).
        backoff: :class:`bool`, default=False
            Wait between queries.

        Returns
        -------
        :class:`list`
            Raw publications.
            Note that integration of those is made in :meth:`~gismap.lab.lab.Lab.get_publications`,
        """
        papers = []
        for db_author in self.sources.values():
            if db_author.is_set:
                papers += db_author.query_publications(s)
                if backoff:
                    sleep(db_author.query_publications_backoff)
            else:
                logger.warning(f"{db_author.name} is not properly identified in {db_author.db_name}.")
        return papers
