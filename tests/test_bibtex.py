"""Unit tests for the BibTeX export module."""

import re

from gismap.sources.bibtex import (
    BIBTEX_TYPES,
    alternate_urls,
    pub_to_bibtex,
    sanitize_cite_key,
)
from gismap.sources.dblp import DBLPAuthor, DBLPPublication
from gismap.sources.hal import HALAuthor, HALPublication
from gismap.sources.ldb import LDBPublication
from gismap.sources.manual import Informal, Outsider
from gismap.sources.models import Author, Publication
from gismap.sources.multi import SourcedPublication


def _has(entry, field):
    return any(line.lstrip().startswith(f"{field} =") for line in entry.splitlines())


def test_sanitize_cite_key_replaces_slashes():
    assert sanitize_cite_key("conf/iptps/Foo08") == "conf_iptps_Foo08"


def test_sanitize_cite_key_keeps_safe_chars():
    assert sanitize_cite_key("a.b-c:d_e") == "a.b-c:d_e"


def test_pub_to_bibtex_minimal_publication():
    p = Publication(title="Foo", authors=[Author(name="Alice Smith")], venue="Nature", type="journal", year=2024)
    p.key = "abc"
    entry = pub_to_bibtex(p)
    assert entry.startswith("@article{abc,")
    assert "title = {Foo}" in entry
    assert "author = {Smith, Alice}" in entry
    assert "year = {2024}" in entry
    assert "journal = {Nature}" in entry


def test_pub_to_bibtex_no_empty_fields():
    p = Publication(title="Foo", authors=[], venue="", type="journal", year=2024)
    p.key = "abc"
    entry = pub_to_bibtex(p)
    assert _has(entry, "year")
    assert not _has(entry, "author")
    assert not _has(entry, "journal")
    assert not _has(entry, "url")
    assert not _has(entry, "abstract")


def test_pub_to_bibtex_dblp_inproceedings_uses_booktitle():
    p = DBLPPublication(
        title="X",
        authors=[DBLPAuthor(name="Bob Jones", key="b/jones")],
        venue="STOC 2024",
        type="conference",
        year=2024,
        key="conf/stoc/Jones24",
    )
    entry = pub_to_bibtex(p)
    assert entry.startswith("@inproceedings{conf_stoc_Jones24,")
    assert _has(entry, "booktitle")
    assert "booktitle = {STOC 2024}" in entry


def test_pub_to_bibtex_hal_with_abstract_and_url():
    p = HALPublication(
        title="A Hal Paper",
        authors=[HALAuthor(name="Carol Doe", key="cdoe")],
        venue="Some Journal",
        type="journal",
        year=2023,
        key="471724",
        metadata={"abstract": "Long abstract.", "url": "https://hal.science/hal-471724"},
    )
    entry = pub_to_bibtex(p)
    assert "abstract = {Long abstract.}" in entry
    assert "url = {https://hal.science/hal-471724}" in entry


def test_pub_to_bibtex_metadata_pages_volume():
    p = DBLPPublication(
        title="X",
        authors=[],
        venue="",
        type="journal",
        year=2024,
        key="key",
        metadata={"pages": "10-20", "volume": "42"},
    )
    entry = pub_to_bibtex(p)
    assert "pages = {10-20}" in entry
    assert "volume = {42}" in entry


def test_pub_to_bibtex_escapes_braces():
    p = Publication(title="Tricky {with} braces", authors=[], venue="", type="report", year=2024)
    p.key = "k"
    entry = pub_to_bibtex(p)
    assert "Tricky \\{with\\} braces" in entry


def test_pub_to_bibtex_unicode_preserved():
    p = Publication(
        title="Étude des résultats", authors=[Author(name="Élie Dupont")], venue="", type="report", year=2024
    )
    p.key = "k"
    entry = pub_to_bibtex(p)
    assert "Étude des résultats" in entry
    assert "Dupont, Élie" in entry


def test_pub_to_bibtex_unknown_type_falls_back_to_misc():
    p = Publication(title="X", authors=[], venue="", type="zoom meeting", year=2024)
    p.key = "k"
    assert pub_to_bibtex(p).startswith("@misc{k,")


def test_pub_to_bibtex_software_type():
    assert BIBTEX_TYPES["software"] == "software"
    p = Publication(title="GisMap", authors=[], venue="", type="software", year=2026)
    p.key = "g"
    assert pub_to_bibtex(p).startswith("@software{g,")


def test_pub_to_bibtex_thesis_type():
    p = Publication(title="X", authors=[], venue="", type="thesis", year=2020)
    p.key = "t"
    assert pub_to_bibtex(p).startswith("@phdthesis{t,")


def test_pub_to_bibtex_informal_uuid_key():
    p = Informal(title="Some chat", authors=[Outsider(name="Dee")])
    entry = pub_to_bibtex(p)
    assert entry.startswith("@unpublished{")
    assert "}" in entry


def test_pub_to_bibtex_multisource_emits_note_with_alt_urls():
    hal = HALPublication(
        title="Same Paper",
        authors=[HALAuthor(name="A", key="a")],
        venue="Nature",
        type="journal",
        year=2024,
        key="hal-1",
        metadata={"url": "https://hal.science/hal-1"},
    )
    dblp = DBLPPublication(
        title="Same Paper",
        authors=[DBLPAuthor(name="A", key="a")],
        venue="Nature",
        type="journal",
        year=2024,
        key="journals/nat/A24",
    )
    sp = SourcedPublication.from_sources([hal, dblp])
    entry = pub_to_bibtex(sp)
    assert _has(entry, "note")
    assert "Also at:" in entry


def test_pub_to_bibtex_monosource_no_note():
    p = HALPublication(
        title="X",
        authors=[],
        venue="",
        type="journal",
        year=2024,
        key="hal-1",
        metadata={"url": "https://hal.science/hal-1"},
    )
    sp = SourcedPublication.from_sources([p])
    entry = pub_to_bibtex(sp)
    assert not _has(entry, "note")


def test_pub_to_bibtex_existing_note_is_preserved():
    p = HALPublication(
        title="X",
        authors=[],
        venue="",
        type="journal",
        year=2024,
        key="hal-1",
        metadata={"note": "Pre-existing note"},
    )
    entry = pub_to_bibtex(p)
    assert "note = {Pre-existing note}" in entry


def test_alternate_urls_skips_sources_without_url():
    hal = HALPublication(
        title="X", authors=[], venue="", type="journal", year=2024, key="h", metadata={"url": "https://hal.science/x"}
    )
    ldb = LDBPublication(title="X", authors=[], venue="", type="journal", year=2024, key="l")
    sp = SourcedPublication.from_sources([hal, ldb])
    urls = alternate_urls(sp)
    assert isinstance(urls, list)
    assert all(u for u in urls)


def _validate_bibtex_document(doc):
    """Lightweight structural validation of a (possibly multi-entry) BibTeX document.

    Returns the number of entries. Raises AssertionError on malformed output:
    unbalanced braces, missing cite key, or stray content between entries (the
    kind of leak the modal "Copy"-button bug produced in the downloaded file).
    """
    assert doc.count("{") == doc.count("}"), "unbalanced braces"
    chunks = [c.strip() for c in re.split(r"\n\s*\n", doc.strip()) if c.strip()]
    for chunk in chunks:
        assert chunk.startswith("@"), f"stray content before an entry: {chunk[:40]!r}"
        assert chunk.endswith("}"), f"entry not properly closed: {chunk[-40:]!r}"
        m = re.match(r"@(\w+)\{([^,\n]+),", chunk)
        assert m and m.group(1) and m.group(2).strip(), f"bad entry header: {chunk[:40]!r}"
    return len(chunks)


def test_multi_entry_document_is_well_formed():
    pubs = [
        Publication(title="First", authors=[Author(name="Alice Smith")], venue="Nature", type="journal", year=2024),
        Publication(
            title="Second {tricky}", authors=[Author(name="Bob Jones")], venue="STOC", type="conference", year=2023
        ),
        Informal(title="A chat", authors=[Outsider(name="Dee")]),
    ]
    for i, p in enumerate(pubs):
        if getattr(p, "key", None) is None:
            p.key = f"k{i}"
    # This is exactly how the lab-level / modal download concatenates entries.
    doc = "\n\n".join(pub_to_bibtex(p) for p in pubs) + "\n"
    assert _validate_bibtex_document(doc) == 3
    assert "Copy" not in doc  # the phantom-"Copy" leak was JS-only; never in the source


def test_pub_to_bibtex_round_trip_parses():
    p = HALPublication(
        title="A test paper",
        authors=[HALAuthor(name="Alice Smith", key="as"), HALAuthor(name="Bob Jones", key="bj")],
        venue="ICML",
        type="conference",
        year=2024,
        key="hal-9000",
        metadata={"url": "https://hal.science/hal-9000", "abstract": "Some abstract."},
    )
    entry = pub_to_bibtex(p)
    assert entry.startswith("@inproceedings{hal-9000,")
    assert entry.endswith("}")
    lines = entry.splitlines()
    assert len(lines) >= 4
    assert all(line.endswith(",") or i in (0, len(lines) - 1, len(lines) - 2) for i, line in enumerate(lines))
