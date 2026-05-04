from collections import defaultdict
from itertools import combinations

import numpy as np

from gismap.sources.bibtex import pub_to_bibtex


def initials(name):
    """
    Parameters
    ----------
    name: :class:`str`
        Person's name.

    Returns
    -------
    :class:`str`
        Person's initials (2 letters only).
    """
    first_letters = [w[0] for w in name.split()]
    return first_letters[0].upper() + first_letters[-1].upper()


def _publication_metadata(pub):
    md = getattr(pub, "metadata", None)
    if md is not None:
        return md
    sources = getattr(pub, "sources", None)
    if sources:
        return getattr(sources[0], "metadata", None) or {}
    return {}


def _resolve_author_url(author):
    url = getattr(author, "url", None)
    if hasattr(author, "metadata"):
        meta_url = getattr(author.metadata, "url", None)
        if meta_url:
            url = meta_url
        elif getattr(author, "sources", None) and hasattr(author.sources[0], "url"):
            url = author.sources[0].url
    return url


def _author_to_dict(author):
    """Compact dict ``{name, url?}`` for an author of any flavor."""
    d = {"name": getattr(author, "name", "Unknown Author")}
    url = _resolve_author_url(author)
    if url:
        d["url"] = url
    return d


def _pub_to_dict(pub):
    """Per-publication payload shipped once to JS.

    Empty fields are dropped to keep the JSON small.
    """
    d = {
        "title": pub.title,
        "year": pub.year,
        "venue": getattr(pub, "venue", "") or "",
        "authors": [_author_to_dict(a) for a in getattr(pub, "authors", []) or []],
        "bib": pub_to_bibtex(pub),
    }
    url = getattr(pub, "url", None)
    if url:
        d["url"] = url
    abstract = _publication_metadata(pub).get("abstract") or ""
    if abstract:
        d["abstract"] = abstract
    return d


def to_node(s, pub_keys):
    """
    Parameters
    ----------
    s: :class:`~gismap.lab.lab_author.LabAuthor`
        Author.
    pub_keys: :class:`list`
        Publication keys associated with this author, year-desc order.

    Returns
    -------
    :class:`dict`
        Display-ready data for the node. Modal HTML is rendered on click by
        the JS layer using ``pub_keys`` and the shared publications dict.
    """
    res = {
        "id": s.key,
        "name": s.name,
        "hover": f"Click for details on {s.name}.",
        "group": s.metadata.group,
        "pub_keys": pub_keys,
    }
    url = _resolve_author_url(s)
    if url:
        res["url"] = url
    if s.metadata.img:
        res.update({"image": s.metadata.img, "shape": "circularImage"})
    else:
        res["label"] = initials(s.name)
    if s.metadata.position:
        x, y = s.metadata.position
        res.update({"x": x, "y": y, "fixed": True})
    return res


def to_edge(k, pub_keys, searchers):
    """
    Parameters
    ----------
    k: :class:`tuple`
        Keys of the two authors.
    pub_keys: :class:`list`
        Joint publication keys, year-desc order.
    searchers: :class:`dict`
        Authors keyed by author key.

    Returns
    -------
    :class:`dict`
        Display-ready data for the collaboration edge.
    """
    strength = 1 + np.log2(len(pub_keys))
    res = {
        "from": k[0],
        "to": k[1],
        "hover": f"Show joint publications from {searchers[k[0]].name} and {searchers[k[1]].name}",
        "width": int(strength),
        "length": int(200 / strength),
        "pub_keys": pub_keys,
    }
    g1, g2 = searchers[k[0]].metadata.group, searchers[k[1]].metadata.group
    if g1 and g2 and g1 != g2:
        res["color"] = "rgba(0,0,0,0)"
    return res


def lab_to_graph(lab):
    """
    Parameters
    ----------
    lab: :class:`~gismap.lab.labmap.LabMap`
        A lab populated with authors and publications.

    Returns
    -------
    :class:`tuple`
        ``(nodes, edges, publications)`` where ``nodes`` and ``edges`` carry
        only display data plus ``pub_keys`` references, and ``publications``
        is a dict keyed by publication key with the full per-pub payload
        (title, authors, venue, year, url, abstract, bib). Modal HTML is
        built JS-side from this shared dict, so each publication is shipped
        only once even when it touches many authors and pairs.

    Examples
    --------

    >>> from gismap.lab import ListMap as Map
    >>> lab = Map(author_list=['Tixeuil Sébastien', 'Mathieu Fabien'], name='mini', dbs="hal")
    >>> lab.update_authors()
    >>> lab.update_publis()
    >>> len(lab.authors)
    2
    >>> 320 < len(lab.publications) < 430
    True
    >>> nodes, edges, pubs = lab_to_graph(lab)
    >>> nodes[0]['group']
    'mini'
    >>> edges[0]['hover']
    'Show joint publications from Mathieu Fabien and Tixeuil Sébastien'
    >>> sample = next(iter(pubs.values()))
    >>> {'title', 'authors', 'bib'} <= set(sample)
    True
    >>> html = lab.html(groups={"mini": {"color": "#777"}})
    """
    node_pubs = defaultdict(list)
    edges_dict = defaultdict(list)
    for p in lab.publications.values():
        # Strange things can happen with multiple sources. This should take care of it.
        lauths = {a.key: a for source in p.sources for a in source.authors if a.__class__.__name__ == "LabAuthor"}
        lauths = sorted([a for a in lauths.values()], key=lambda a: str(a.key))
        for a in lauths:
            node_pubs[a.key].append(p)
        for a1, a2 in combinations(lauths, 2):
            edges_dict[a1.key, a2.key].append(p)
    for k, v in node_pubs.items():
        node_pubs[k] = [p.key for p in sorted(v, key=lambda p: -p.year)]
    for k, v in edges_dict.items():
        edges_dict[k] = [p.key for p in sorted(v, key=lambda p: -p.year)]

    nodes = [to_node(s, node_pubs.get(s.key, [])) for s in lab.authors.values()]
    edges = [to_edge(k, v, lab.authors) for k, v in edges_dict.items()]
    publications = {pk: _pub_to_dict(p) for pk, p in lab.publications.items()}

    return nodes, edges, publications
