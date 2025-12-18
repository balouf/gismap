from gismo import MixInIO
from tqdm.auto import tqdm
from IPython.display import display, HTML
from pathlib import Path

from gismap.utils.common import list_of_objects
from gismap.utils.logger import logger
from gismap.lab.lab_author import (
    db_dict,
    default_dbs,
    AuthorMetadata,
    LabAuthor,
    labify_publications,
)
from gismap.sources.multi import (
    regroup_authors,
    regroup_publications,
)
from gismap.lab.expansion import proper_prospects
from gismap.lab.filters import (
    author_taboo_filter,
    publication_taboo_filter,
    publication_size_filter,
    publication_oneword_filter,
)
from gismap.gisgraphs.builder import make_vis


class LabMap(MixInIO):
    """
    Abstract class for labs.

    Actual Lab classes can be created by implementing the `_author_iterator` method.

    Labs can be saved with the `dump` method and loaded with the `load` method.

    Parameters
    ----------
    name: :class:`str`
        Name of the lab. Can be set as class or instance attribute.
    dbs: :class:`list`, default=[:class:`~gismap.sources.hal.HAL`, :class:`~gismap.sources.dblp.DBLP`]
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
        return f"Lab {self.name}"

    def _author_iterator(self):
        """
        Yields
        ------
        :class:`~gismap.lab.lab.LabAuthor`
        """
        raise NotImplementedError

    def update_authors(self, desc="Author information"):
        """
        Populate the authors attribute (:class:`dict` [:class:`str`, :class:`~gismap.lab.lab.LabAuthor`]).

        Returns
        -------
        None
        """
        self.authors = dict()
        for author in tqdm(self._author_iterator(), desc=desc):
            if not all(f(author) for f in self.author_selectors):
                continue
            if len(author.sources) == 0:
                author.auto_sources(dbs=list_of_objects(self.dbs, db_dict, default=default_dbs))
            if author.sources:
                self.authors[author.key] = author
            if author.metadata.img is None:
                author.auto_img()
            if author.metadata.group is None:
                author.metadata.group = self.name

    def update_publis(self, desc="Publications information"):
        """
        Populate the publications attribute (:class:`dict` [:class:`str`, :class:`~gismap.sources.multi.SourcedPublication`]).

        Returns
        -------
        None
        """
        pubs = dict()
        for author in tqdm(self.authors.values(), desc=desc):
            pubs.update(
                author.get_publications(
                    clean=False, selector=self.publication_selectors
                )
            )
        regroup_authors(self.authors, pubs)
        self.publications = regroup_publications(pubs)

    def expand(self, target=None, group="moon", desc="Moon information", **kwargs):
        if target is None:
            target = len(self.authors) // 3
        old, rosetta = proper_prospects(self, max_new=target, **kwargs)
        new = {a.key: a for a in rosetta.values()}
        for k, v in old.items():
            rosetta[k] = self.authors[v]
        logger.debug(f"{len(new)} new authors selected")
        if len(new) == 0:
            logger.warning("Expansion failed: no new author found.")
            return None

        self.authors.update(new)

        pubs = dict()
        for author in tqdm(new.values(), desc=desc):
            author.auto_img()
            author.metadata.group = group
            pubs.update(
                author.get_publications(
                    clean=False, selector=self.publication_selectors
                )
            )

        for pub in self.publications.values():
            for source in pub.sources:
                pubs[source.key] = source

        labify_publications(pubs.values(), rosetta)

        self.publications = regroup_publications(pubs)

        return None

    def html(self, **kwargs):
        return make_vis(self, **kwargs)

    def save_html(self, name=None, **kwargs):
        if name is None:
            name = self.name
        name = Path(name).with_suffix(".html")
        with open(name, "wt", encoding="utf8") as f:
            f.write(self.html(**kwargs))

    def show_html(self, **kwargs):
        display(HTML(self.html(**kwargs)))


class ListMap(LabMap):
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
