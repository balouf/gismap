"""BibTeX export for individual publications.

Lab-level aggregation lives in :meth:`gismap.lab.labmap.LabMap.to_bib`; this
module only handles per-publication formatting so it stays decoupled from
the lab layer.
"""

import hashlib
import re

#: Mapping from GisMap normalized publication types to BibTeX entry types.
#: Unknown types fall back to ``misc``.
BIBTEX_TYPES = {
    "journal": "article",
    "conference": "inproceedings",
    "book": "book",
    "chapter": "incollection",
    "thesis": "phdthesis",
    "hdr": "phdthesis",
    "report": "techreport",
    "software": "software",
    "unpublished": "unpublished",
}

_CITE_KEY_RE = re.compile(r"[^A-Za-z0-9:_\-.]")


def sanitize_cite_key(key):
    """
    Coerce a publication key to a BibTeX-safe cite key.

    Replaces every character outside ``[A-Za-z0-9:_\\-.]`` with ``_``. This
    handles DBLP keys like ``conf/iptps/Foo`` (slashes), HAL numeric keys, and
    UUID hex keys from manual publications.

    Parameters
    ----------
    key: :class:`str`
        Source key.

    Returns
    -------
    :class:`str`
        Sanitized cite key.

    Examples
    --------
    >>> sanitize_cite_key("conf/iptps/BoufkhadMMPV08")
    'conf_iptps_BoufkhadMMPV08'
    >>> sanitize_cite_key("471724")
    '471724'
    >>> sanitize_cite_key("a b/c.d-e:f")
    'a_b_c.d-e:f'
    """
    return _CITE_KEY_RE.sub("_", str(key))


def _fallback_cite_key(pub):
    h = hashlib.md5(pub.fingerprint.encode("utf-8")).hexdigest()[:10]
    return f"pub_{h}"


def _bibtex_escape(value):
    """Escape backslashes and braces in a BibTeX field value."""
    s = str(value)
    s = s.replace("\\", "\\\\")
    s = s.replace("{", "\\{").replace("}", "\\}")
    return s


def _format_authors(authors):
    """
    Render a list of authors in BibTeX ``Last, First and Last, First`` form.

    Heuristic: the last whitespace-separated token of ``author.name`` is the
    surname; everything before is the given names. Names already containing a
    comma are kept verbatim. Names with a single token are kept as-is. Authors
    with non-trivial particles ("de", "von", "van der") may need post-editing.
    """
    out = []
    for a in authors:
        name = getattr(a, "name", str(a)).strip()
        if not name:
            continue
        if "," in name:
            out.append(name)
            continue
        parts = name.split()
        if len(parts) == 1:
            out.append(parts[0])
        else:
            out.append(f"{parts[-1]}, {' '.join(parts[:-1])}")
    return " and ".join(out)


def _publication_metadata(pub):
    """Return the metadata dict relevant for BibTeX export.

    For source-specific publications (HAL/DBLP/LDB/Informal) this is
    ``pub.metadata``. For :class:`SourcedPublication` (which has no metadata
    of its own) it is the primary source's metadata.
    """
    md = getattr(pub, "metadata", None)
    if md is not None:
        return md
    sources = getattr(pub, "sources", None)
    if sources:
        return getattr(sources[0], "metadata", None) or {}
    return {}


def _venue_field(bibtex_type):
    if bibtex_type == "article":
        return "journal"
    if bibtex_type in ("inproceedings", "incollection"):
        return "booktitle"
    return None


def alternate_urls(pub):
    """URLs of the non-primary sources, in order. Empty for mono-source pubs."""
    sources = getattr(pub, "sources", None)
    if not sources or len(sources) < 2:
        return []
    return [u for u in (getattr(s, "url", None) for s in sources[1:]) if u]


def pub_to_bibtex(pub):
    """
    Render a single :class:`~gismap.sources.models.Publication` as a BibTeX entry.

    Empty fields are never emitted. Fields included when present:

    - ``title``, ``author``, ``year``
    - ``journal`` / ``booktitle`` (depending on entry type)
    - ``url`` (primary source URL)
    - ``abstract`` (HAL only, when available)
    - ``pages``, ``volume`` (DBLP)
    - ``note`` aggregating any pre-existing ``metadata['note']`` and the URLs
      of non-primary sources for :class:`SourcedPublication` (``Also at: …``).

    Cite key is :func:`sanitize_cite_key` applied to ``pub.key``, with a
    fingerprint-based fallback if the key is missing.

    Parameters
    ----------
    pub: :class:`~gismap.sources.models.Publication`
        Any publication subclass (HAL, DBLP, LDB, Informal, SourcedPublication).

    Returns
    -------
    :class:`str`
        BibTeX entry, terminated by ``}`` (no trailing newline).

    Examples
    --------
    >>> from gismap.sources.models import Author, Publication
    >>> p = Publication(title="A Tale", authors=[Author(name="Alice Smith")],
    ...                 venue="Nature", type="journal", year=2024)
    >>> p.key = "abc/123"
    >>> print(pub_to_bibtex(p))
    @article{abc_123,
      title = {A Tale},
      author = {Smith, Alice},
      year = {2024},
      journal = {Nature}
    }
    """
    bibtex_type = BIBTEX_TYPES.get(pub.type, "misc")
    raw_key = getattr(pub, "key", None)
    cite_key = sanitize_cite_key(raw_key) if raw_key else _fallback_cite_key(pub)

    fields = []

    if pub.title:
        fields.append(("title", pub.title))

    authors_str = _format_authors(pub.authors or [])
    if authors_str:
        fields.append(("author", authors_str))

    if pub.year:
        fields.append(("year", pub.year))

    venue_key = _venue_field(bibtex_type)
    if venue_key and pub.venue:
        fields.append((venue_key, pub.venue))

    url = getattr(pub, "url", None)
    if url:
        fields.append(("url", url))

    metadata = _publication_metadata(pub)
    for src_key, bib_key in [("abstract", "abstract"), ("pages", "pages"), ("volume", "volume")]:
        v = metadata.get(src_key)
        if v:
            fields.append((bib_key, v))

    note_parts = []
    user_note = metadata.get("note")
    if user_note:
        note_parts.append(str(user_note))
    alt = alternate_urls(pub)
    if alt:
        note_parts.append("Also at: " + "; ".join(alt))
    if note_parts:
        fields.append(("note", ". ".join(note_parts)))

    lines = [f"@{bibtex_type}{{{cite_key},"]
    for k, v in fields[:-1]:
        lines.append(f"  {k} = {{{_bibtex_escape(v)}}},")
    if fields:
        k, v = fields[-1]
        lines.append(f"  {k} = {{{_bibtex_escape(v)}}}")
    lines.append("}")
    return "\n".join(lines)
