from domonic import tags
from itertools import combinations
from collections import defaultdict
import numpy as np


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


def linkify(name, url):
    if url:
        return f'<a href="{url}" target="_blank">{name}</a>'
    else:
        return f'<span>{name}</span>'


def author_html(author):
    """
    Parameters
    ----------
    author: :class:`~gismap.sources.models.Author`
        Searcher.

    Returns
    -------
    HTML string with URL if applicable.
    """
    name = getattr(author, "name", "Unknown Author")
    # Try direct URL property (optional)
    url = getattr(author, "url", None)
    # For LabAuthor, check metadata.url
    if hasattr(author, "metadata"):
        meta_url = getattr(author.metadata, "url", None)
        if meta_url:
            url = meta_url
        elif hasattr(author.sources[0], "url"):
            url = author.sources[0].url
    return linkify(name, url)


def pub_html(pub):
    """
    Parameters
    ----------
    pub: :class:`~gismap.sources.models.Publication`
        Publication.

    Returns
    -------
    HTML string with hyperlinks where applicable.
    """
    # Title as link if available
    url = getattr(pub, "url", None)
    if url is None and hasattr(pub, "sources"):
        url = getattr(pub.sources[0], "url", None)
    title_html = linkify(pub.title, url)

    # Authors: render in order, separated by comma
    authors_html = ", ".join([
        author_html(author) for author in getattr(pub, "authors", [])
    ])

    # Venue, Year
    venue = getattr(pub, "venue", "")
    year = getattr(pub, "year", "")

    # Basic HTML layout
    html = f"{title_html}, by <i>{authors_html}</i>. {venue}, {year}."
    return html.strip()


expand_script = """var elts = this.parentElement.parentElement.querySelectorAll('.extra-publication');
for (var i = 0; i < elts.length; ++i) {elts[i].style.display = 'list-item';}
this.parentElement.style.display = 'none';
return false;"""


def publications_list(publications, n=10):
    """
    Parameters
    ----------
    publications: :class:`list` of :class:`~gismap.sources.models.Publication`
        Publications to display.
    n: :class:`int`, default=10
        Number of publications to display. If there are more publications, a *Show more* option is available to unravel them.

    Returns
    -------
    :class:`~domonic.html.ul`
    """
    lis = []
    for i, pub in enumerate(publications):
        if i < n:
            lis.append(f"<li>{pub_html(pub)}</li>")
        else:
            lis.append(f'<li class="extra-publication" style="display:none;">{pub_html(pub)}</li>')
    if len(publications) > n:
        lis.append(f'<li><a href="#" onclick="{expand_script}">Show more…</a></li>')
    return "<ul>\n"+'\n'.join(lis)+"</ul>\n"


def to_node(s, node_pubs):
    """
    Parameters
    ----------
    s: :class:`~gismap.lab.lab_author.LabAuthor`
        Searcher.
    node_pubs: :class:`dict`
        Lab publications.

    Returns
    -------
    :class:`dict`
        A display-ready representation of the searcher.
    """
    overlay = tags.div()
    overlay.appendChild(tags.div(f"Publications of {author_html(s)}"))
    overlay.appendChild(tags.div(publications_list(node_pubs[s.key])))

    res = {
        "id": s.key,
        "hover": f"Click for details on {s.name}.",
        "overlay": f"{overlay}",
        "group": s.metadata.group,
    }
    if s.metadata.img:
        res.update({"image": s.metadata.img, "shape": "circularImage"})
    else:
        res["label"] = initials(s.name)
    if s.metadata.position:
        x, y = s.metadata.position
        res.update({"x": x, "y": y, "fixed": True})
    return res


def to_edge(k, v, searchers):
    """
    Parameters
    ----------
    k: :class:`tuple`
        Keys of the searchers involved.
    v: :class:`list`
        List of joint publications.
    searchers: :class:`dict`
        Searchers.

    Returns
    -------
    :class:`dict`
        A display-ready representation of the collaboration edge.
    """
    strength = 1 + np.log2(len(v))
    overlay = tags.div()
    overlay.appendChild(tags.div(f"Joint publications from {author_html(searchers[k[0]])} and {author_html(searchers[k[1]])}:"))
    overlay.appendChild(tags.div(f"{publications_list(v)}"))
    res = {
        "from": k[0],
        "to": k[1],
        "hover": f"Show joint publications from {searchers[k[0]].name} and {searchers[k[1]].name}",
        "overlay": f"{overlay}",
        "width": int(strength),
        "length": int(200 / strength),
    }
    g1, g2 = searchers[k[0]].metadata.group, searchers[k[1]].metadata.group
    if g1 and g2 and g1 != g2:
        res['color'] = "rgba(0,0,0,0)"
    return res


def lab_to_graph(lab):
    """
    Parameters
    ----------
    lab: :class:`~gismap.lab.labmap.LabMap`
        A lab populated with searchers and publications.

    Returns
    -------
    :class:`str`
        Collaboration graph.

    Examples
    --------

    >>> from gismap.lab import ListMap as Map
    >>> lab = Map(author_list=['Tixeuil Sébastien', 'Mathieu Fabien'], name='mini')
    >>> lab.update_authors()
    >>> lab.update_publis()
    >>> len(lab.authors)
    2
    >>> 380 < len(lab.publications) < 440
    True
    >>> nodes, edges = lab_to_graph(lab)
    >>> nodes[0]['group']
    'mini'
    >>> edges[0]['hover']
    'Show joint publications from Mathieu Fabien and Tixeuil Sébastien'
    """
    node_pubs = defaultdict(list)  # {k: [] for k in lab.authors}
    edges_dict = defaultdict(list)
    for p in lab.publications.values():
        # Strange things can happen with multiple sources. This should take care of it.
        lauths = {
            a.key: a
            for source in p.sources
            for a in source.authors
            if a.__class__.__name__ == "LabAuthor"
        }
        lauths = sorted([a for a in lauths.values()], key=lambda a: str(a.key))
        for a in lauths:
            node_pubs[a.key].append(p)
        for a1, a2 in combinations(lauths, 2):
            edges_dict[a1.key, a2.key].append(p)
    connected = {k for kl in edges_dict for k in kl}
    for k, v in node_pubs.items():
        node_pubs[k] = sorted(v, key=lambda p: -p.year)
    for k, v in edges_dict.items():
        edges_dict[k] = sorted(v, key=lambda p: -p.year)
    nodes = [
        to_node(s, node_pubs)
        for s in lab.authors.values()  # if s.key in connected
    ]
    edges = [to_edge(k, v, lab.authors) for k, v in edges_dict.items()]
    for node in nodes:
        node['connected'] = node['id'] in connected

    return nodes, edges
