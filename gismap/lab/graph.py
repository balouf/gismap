import numpy as np
from collections import defaultdict
from itertools import combinations
from gismap.lab.vis import generate_html


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
    return first_letters[0] + first_letters[-1]


def author_to_html(author):
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
    if url:
        return f'<a href="{url.strip()}" target="_blank">{name}</a>'
    else:
        return name


def publication_to_html(pub):
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
    if url:
        title_html = f'<a href="{url}" target="_blank">{pub.title}</a>'
    else:
        title_html = pub.title

    # Authors: render in order, separated by comma
    author_html_list = [
        author_to_html(author) for author in getattr(pub, "authors", [])
    ]
    authors_html = ", ".join(author_html_list)

    # Venue, Year
    venue = getattr(pub, "venue", "")
    year = getattr(pub, "year", "")

    # Basic HTML layout
    html = f"{title_html}, by <i>{authors_html}</i>. {venue}, {year}."
    return html.strip()


def publications_list_html(publications, n=10):
    """

    Parameters
    ----------
    publications: :class:`list` of :class:`~gismap.sources.models.Publication`
        Publications to display.
    n: :class:`int`, default=10
        Number of publications to display. If there are more publications, a *Show more* option is available to unravel them.

    Returns
    -------
    :class:`str`
    """
    list_items = []
    for i, pub in enumerate(publications):
        item = publication_to_html(pub)
        if i < n:
            li = f"<li>{item}</li>"
        else:
            li = f'<li class="extra-publication" style="display:none;">{item}</li>'
        list_items.append(li)
    ul_content = "\n".join(list_items)

    if len(publications) <= n:
        show_more_part = ""
    else:
        # Add a "Show more" link and JavaScript for toggling
        show_more_part = """
<li>
  <a href="#" onclick="
    var elts = this.parentElement.parentElement.querySelectorAll('.extra-publication');
    for (var i = 0; i < elts.length; ++i) {elts[i].style.display = 'list-item';}
    this.parentElement.style.display = 'none';
    return false;">Show more…</a>
</li>
        """

    html = f"""<ul>
{ul_content}
{show_more_part}
</ul>
"""
    return html


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
    res = {
        "id": s.key,
        "hover": f"Click for details on {s.name}.",
        "overlay": f"<div> Publications of {author_to_html(s)}:</div><div>{publications_list_html(node_pubs[s.key])}</div>",
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
    return {
        "from": k[0],
        "to": k[1],
        "hover": f"Show joint publications from {searchers[k[0]].name} and {searchers[k[1]].name}",
        "overlay": f"<div> Joint publications from {author_to_html(searchers[k[0]])} and {author_to_html(searchers[k[1]])}:</div><div>{publications_list_html(v)}</div>",
        "width": int(strength),
        "length": int(200 / strength),
    }


def lab2graph(lab):
    """
    Parameters
    ----------
    lab: :class:`~gismap.lab.lab.Lab`
        A lab populated with searchers and publications.

    Returns
    -------
    :class:`str`
        Collaboration graph.

    Examples
    --------

    >>> from gismap.lab import ListLab
    >>> lab = ListLab(author_list=['Tixeuil Sébastien', 'Mathieu Fabien'], name='mini')
    >>> lab.update_authors()
    >>> lab.update_publis()
    >>> len(lab.authors)
    2
    >>> 430 < len(lab.publications) < 440
    True
    >>> html = lab2graph(lab)
    >>> html[:80]  # doctest: +ELLIPSIS
    '\\n<div id="mynetwork_..."></div>\\n<div id="modal_..." class="modal">\\n  <'
    """
    node_pubs = {k: [] for k in lab.authors}
    edges_dict = defaultdict(list)
    for p in lab.publications.values():
        # Strange things can happen with multiple sources. This should take care of it.
        lauths = {a.key: a for source in p.sources for a in source.authors if a.__class__.__name__ == "LabAuthor"}
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

    return generate_html(
        nodes=[
            to_node(s, node_pubs) for s in lab.authors.values() if s.key in connected
        ],
        edges=[to_edge(k, v, lab.authors) for k, v in edges_dict.items()],
    )
