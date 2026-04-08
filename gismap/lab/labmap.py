from pathlib import Path

from gismo import MixInIO
from IPython.display import HTML, display
from tqdm.auto import tqdm

from gismap.gisgraphs.builder import make_vis
from gismap.lab.expansion import proper_prospects
from gismap.lab.filters import (
    author_taboo_filter,
    publication_oneword_filter,
    publication_size_filter,
    publication_taboo_filter,
)
from gismap.lab.lab_author import (
    AuthorMetadata,
    LabAuthor,
    db_dict,
    default_dbs,
)
from gismap.sources.manual import Informal
from gismap.sources.multi import (
    SourcedPublication,
    regroup_authors,
    regroup_publications,
)
from gismap.utils.common import list_of_objects
from gismap.utils.fuzzy import similarity_matrix
from gismap.utils.logger import logger


class LabMap(MixInIO):
    """
    Abstract class for labs.

    Actual Lab classes can be created by implementing the `_author_iterator` method.

    Labs can be saved with the `dump` method and loaded with the `load` method.

    Parameters
    ----------
    name: :class:`str`
        Name of the lab. Can be set as class or instance attribute.
    dbs: :class:`list`, default=[:class:`~gismap.sources.hal.HAL`, :class:`~gismap.sources.ldb.LDB`]
        List of DB sources to use.


    Attributes
    -----------

    author_selectors: :class:`list`
        Author filters. Default: minimal filtering.
    publication_selectors: :class:`list`
        Publication filter. Default: less than 10 authors, not an editorial, at least two words in the title.
    """

    name = None
    dbs = default_dbs

    def __init__(self, name=None, dbs=None):
        if name is not None:
            self.name = name
        self.dbs = dbs
        self.author_selectors = [author_taboo_filter()]
        self.publication_selectors = [
            publication_size_filter(),
            publication_taboo_filter(),
            publication_oneword_filter(),
        ]
        self.authors = None
        self.publications = None

    def __repr__(self):
        return f"LabMap('{self.name}')"

    def __str__(self):
        n_auth = len(self.authors) if self.authors else "?"
        n_pub = len(self.publications) if self.publications else "?"
        return f"LabMap of {self.name} ({n_auth} authors, {n_pub} publications)"

    def _author_iterator(self):
        """
        Yields
        ------
        :class:`~gismap.lab.lab_author.LabAuthor`
        """
        raise NotImplementedError

    def update_authors(self, desc="Author information"):
        """
        Populate the authors attribute (:class:`dict` [:class:`str`, :class:`~gismap.lab.lab_author.LabAuthor`]).

        Returns
        -------
        None
        """
        self.authors = dict()
        for author in tqdm(self._author_iterator(), desc=desc):
            if not all(f(author) for f in self.author_selectors):
                continue
            author.auto_sources(dbs=list_of_objects(self.dbs, db_dict(), default=default_dbs))
            if author.sources:
                self.authors[author.key] = author
            if author.metadata.img is None:
                author.auto_img()
            if author.metadata.group is None:
                author.metadata.group = self.name

    def update_publis(self, desc="Publications information"):
        """
        Populate the publications attribute
        (:class:`dict` [:class:`str`, :class:`~gismap.sources.multi.SourcedPublication`]).

        Returns
        -------
        None
        """
        pubs = dict()
        for author in tqdm(self.authors.values(), desc=desc):
            pubs.update(author.get_publications(clean=False, selector=self.publication_selectors))
        regroup_authors(self.authors, pubs)
        self.publications = regroup_publications(pubs)

    def expand(self, target=None, group="moon", desc="Moon information", **kwargs):
        """
        Expand the lab with external collaborators found in publications.

        Discovers authors who co-published with lab members, ranks them by
        collaboration strength, and adds the top candidates.

        Parameters
        ----------
        target : :class:`int`, optional
            Number of new authors to add. Defaults to ``len(self.authors) // 3``.
        group : :class:`str`, default="moon"
            Group label assigned to new authors.
        desc : :class:`str`, default="Moon information"
            Progress bar description.
        **kwargs
            Passed to :func:`~gismap.lab.expansion.proper_prospects`.
        """
        if target is None:
            target = len(self.authors) // 3
        new_authors = proper_prospects(self, max_new=target, **kwargs)
        if not new_authors:
            logger.warning("Expansion failed: no new author found.")
            return
        logger.debug(f"{len(new_authors)} new authors selected")

        pubs = dict()
        for author in tqdm(new_authors, desc=desc):
            author.auto_img()
            author.metadata.group = group
            pubs.update(author.get_publications(clean=False, selector=self.publication_selectors))
        for pub in self.publications.values():
            for source in pub.sources:
                pubs[source.key] = source

        self.authors.update({a.key: a for a in new_authors})
        regroup_authors(self.authors, pubs)
        self.publications = regroup_publications(pubs)

    def html(self, **kwargs):
        """
        Generate HTML representation of the collaboration graph.

        Parameters
        ----------
        **kwargs
            Passed to :func:`~gismap.gisgraphs.builder.make_vis`.

        Returns
        -------
        :class:`str`
            HTML content as a string.
        """
        return make_vis(self, **kwargs)

    def save_html(self, name=None, **kwargs):
        """
        Save the collaboration graph as an HTML file.

        Parameters
        ----------
        name: :class:`str`, optional
            Output filename. Defaults to lab name.
        **kwargs
            Passed to :meth:`html`.

        Returns
        -------
        None
        """
        if name is None:
            name = self.name
        name = Path(name).with_suffix(".html")
        with open(name, "w", encoding="utf8") as f:
            f.write(self.html(**kwargs))

    def show_html(self, **kwargs):
        """
        Display the collaboration graph in a Jupyter notebook.

        Parameters
        ----------
        **kwargs
            Passed to :meth:`html`.

        Returns
        -------
        None
        """
        display(HTML(self.html(**kwargs)))

    def add_publication(self, title, authors, **kwargs):
        """
        Add a manual publication to the lab.

        Author names given as strings are resolved to known authors from the lab's
        publications using fuzzy matching. Unmatched names become
        :class:`~gismap.sources.manual.Outsider` instances.

        Parameters
        ----------
        title : :class:`str`
            Publication title.
        authors : :class:`list`
            Author names (:class:`str`) or author objects.
        **kwargs
            Passed to :class:`~gismap.sources.manual.Informal` (``venue``, ``type``,
            ``year``, ``key``, ``metadata``) and to
            :func:`~gismap.sources.manual.fit_names` (``threshold``, ``n_range``,
            ``length_impact``).
        """
        fit_kwargs = {k: kwargs.pop(k) for k in ["threshold", "n_range", "length_impact"] if k in kwargs}
        pub = Informal(title=title, authors=list(authors), **kwargs)
        pub.fit_authors(self, **fit_kwargs)
        pub = SourcedPublication.from_sources([pub])
        self.publications[pub.key] = pub

    def select_publications(self, query, n_range=4, length_impact=0.001, threshold=80):
        """
        Search for publications matching a query.

        Parameters
        ----------
        query : :class:`str` or :class:`callable`
            If a string, matches by exact key or fuzzy title similarity.
            If a callable, used as a filter ``f(pub) -> bool`` on each publication.
        n_range : :class:`int`, default=4
            Passed to :func:`~gismap.utils.fuzzy.similarity_matrix`.
        length_impact : :class:`float`, default=0.001
            Passed to :func:`~gismap.utils.fuzzy.similarity_matrix`.
        threshold : :class:`int`, default=80
            Minimum similarity score (0-100) for fuzzy title matching.

        Returns
        -------
        :class:`list`
            Matching publications.
        """
        if isinstance(query, str):
            if query in self.publications:
                candidates = [self.publications[query]]
            else:
                jc = similarity_matrix(
                    self.publications.values(),
                    key=lambda p: p.title,
                    candidates=[query],
                    key2=lambda q: q,
                    n_range=n_range,
                    length_impact=length_impact,
                )
                candidates = [p for p, s in zip(self.publications.values(), jc[0]) if s >= threshold]
        else:
            candidates = [p for p in self.publications.values() if query(p)]
        n = len(candidates)
        match n:
            case 0:
                logger.info("No match found for query.")
                return []
            case 1:
                logger.info("1 publication found.")
            case _:
                logger.info(f"{n} publications found.")
        return candidates

    def del_publication(self, query, confirm=True, **kwargs):
        """
        Remove publications matching a query from the lab.

        Parameters
        ----------
        query : :class:`str` or :class:`callable`
            Passed to :meth:`select_publications`.
        confirm : :class:`bool`, default=True
            If True, display matches and prompt for confirmation before deletion.
        **kwargs
            Passed to :meth:`select_publications`.
        """
        candidates = self.select_publications(query, **kwargs)
        if len(candidates) == 0:
            return
        prompt = "The following publications have been selected:\n"
        prompt += "\n".join(p.short_str() for p in candidates)
        prompt += f"\nConfirm their deletion from the {self.__class__.__name__} of {self.name} (y/N):"
        if not confirm or (input(prompt).lower().strip() or "N") in ["y", "yes"]:
            for p in candidates:
                del self.publications[p.key]
            logger.info(f"{len(candidates)} publication(s) removed.")
        else:
            logger.info("Publication deletion aborted")


class ListMap(LabMap):
    """
    Simplest way to create a lab: with a list of names.

    Parameters
    ----------
    author_list: :class:`list` of :class:`str`
        List of authors names.
    args: :class:`list`
        Arguments to pass to the :class:`~gismap.lab.labmap.LabMap` constructor.
    kwargs: :class:`dict`
        Keyword arguments to pass to the :class:`~gismap.lab.labmap.LabMap` constructor.
    """

    def __init__(self, author_list, *args, **kwargs):
        self.author_list = author_list
        super().__init__(*args, **kwargs)

    def _author_iterator(self):
        for name in self.author_list:
            yield LabAuthor(name=name, metadata=AuthorMetadata())
