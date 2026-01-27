from collections import defaultdict
from string import Template

from gismap.utils.text import reduce_keywords, Corrector


class SearchAction:
    """
    Base class for extracting search results from a Gismo.

    Subclasses should implement :meth:`process` to define
    how to extract results from the gismo.

    Parameters
    ----------
    name : :class:`str`, optional
        Name of this action (used as key in results dict).
    post : callable, optional
        Post-processing function applied to results.
    """

    def __init__(self, name=None, post=None):
        self.name = name
        self.post = (lambda x: x) if post is None else post

    def process(self, gismo):
        """
        Extract results from the gismo. Must be implemented by subclasses.

        Parameters
        ----------
        gismo : :class:`~gismo.gismo.Gismo`
            The gismo to query.

        Returns
        -------
        Results (type depends on subclass).
        """
        raise NotImplementedError

    def run(self, gismo):
        """
        Execute the action and apply post-processing.

        Parameters
        ----------
        gismo : :class:`~gismo.gismo.Gismo`
            The gismo to query.

        Returns
        -------
        Post-processed results.
        """
        return self.post(self.process(gismo))


def p2t(publis):
    """
    Parameters
    ----------
    publis: :class:`list`
        List of publications

    Returns
    -------
    :class:`str`
        Publications converted in text and concatenated.
    """
    return "\n".join(a.string for a in publis)


def l2t(lis):
    """

    Parameters
    ----------
    lis: :class:`list`
        List of text.
    Returns
    -------
    :class:`str`
        Concatenation, comma-separated.
    """
    return ", ".join(lis)


class SearchDocuments(SearchAction):
    """Gives *k* best covering articles."""

    def __init__(self, name="articles", post=None, k=5):
        if post is None:
            post = p2t
        super().__init__(name=name, post=post)
        self.k = k

    def process(self, gismo):
        return gismo.get_documents_by_coverage(k=self.k)


class SearchFeatures(SearchAction):
    """Gives best keywords."""

    def __init__(self, name="keywords", post=None):
        if post is None:
            post = l2t
        super().__init__(name=name, post=post)

    def process(self, gismo):
        return reduce_keywords(gismo.get_features_by_rank())


class SearchLandmarks(SearchAction):
    """Gives best landmarks."""

    def __init__(self, name="landmarks", post=None, lmks=None):
        if post is None:
            post = l2t
        super().__init__(name=name, post=post)
        self.lmks = lmks

    def process(self, gismo):
        return self.lmks.get_landmarks_by_rank(gismo)


class Search:
    """
    Builds a gismo search engine.

    Parameters
    ----------
    gismo: :class:`~gismo.gismo.Gismo`
        Gismo to use.
    action_list: :class:`list`
        List of actions to perform.
    post: callable, optional
        Output transformation.
    corrector: :class:`Bool`, default=True
        Implement word correction.
    """

    def __init__(self, gismo, action_list, post=None, corrector=True):
        self.gismo = gismo
        self.action_list = action_list
        self.post = (lambda x: x) if post is None else post
        if corrector:
            self.corrector = Corrector(gismo.embedding.features)
        else:
            self.corrector = None

    def __call__(self, query):
        if self.corrector is not None:
            query = self.corrector(query)
        success = self.gismo.rank(query)
        res = dict()
        if success:
            for action in self.action_list:
                res[action.name] = action.run(self.gismo)
        return self.post({"query": query, "success": success, "results": res})


def search_to_text(res):
    """
    Parameters
    ----------
    res: :class:`dict`
        Raw results of search.

    Returns
    -------
    :class:`str`
        Text representation of the results.
    """
    query = res["query"]
    if not res["success"]:
        return f"Failure: ``{query}'' not found!"
    output = f"Results for ``{query}'':\n"
    for k, v in res["results"].items():
        output += f"Suggested {k}: {v}\n"
    return output


publi_template = Template("""
<li>
<i>$title</i>, by $authors. $venue, $year. $hal $dblp
</li>
""")


def publi_to_html(publi):
    """
    Convert a publication to an HTML list item.

    Parameters
    ----------
    publi : :class:`~gismap.sources.models.Publication`
        Publication to convert.

    Returns
    -------
    :class:`str`
        HTML list item string.
    """
    dico = dict()
    for db in ["hal", "dblp"]:
        source = publi.sources.get(db)
        if source:
            dico[db] = f"<a href='{source['url']}' target='_blank'>{db.upper()}</a>"
        else:
            dico[db] = ""
    dico["authors"] = ", ".join(a.name for a in publi.authors)
    for key in ["title", "venue", "year"]:
        dico[key] = getattr(publi, key)
    return publi_template.substitute(dico)


def publis_to_html(publis):
    """
    Convert a list of publications to an HTML unordered list.

    Parameters
    ----------
    publis : :class:`list`
        List of publications.

    Returns
    -------
    :class:`str`
        HTML unordered list string.
    """
    rows = "\n".join(publi_to_html(p) for p in publis)
    return f"<ul>\n{rows}\n</ul>"


html_template = Template("""
<div>
<h4>Search: <i>$query</i></h4>
<div>
<h5>Associated keywords:</h5>
<div>$keywords</div>
</div>
<div>
<h5>Associated Projects:</h5>
<div>$projects</div>
</div>
<div>
<h5>Suggested people:</h5>
<div>$members</div>
</div>
<div>
<h5>Suggested publications:</h5>
<div>$publis</div>
</div>
</div>

""")


def search_to_html(res):
    """
    Parameters
    ----------
    res: :class:`dict`
        Raw results of search.

    Returns
    -------
    :class:`str`
        HTML representation of the results.
    """
    dico = defaultdict(str)
    dico.update(res["results"])
    dico["query"] = res["query"]
    if res["success"]:
        dico["publis"] = publis_to_html(dico["articles"])
    return html_template.safe_substitute(dico)
