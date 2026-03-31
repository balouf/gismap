"""Tests for the DBLP TTL parser."""

import gzip
import tempfile
from pathlib import Path

from gismap.sources.dblp_ttl import parse_block, publis_streamer

TTL_EXAMPLE = """\
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

<https://dblp.org/rec/reference/vision/Singh14>
dblp:title "Transparency and Translucency." ;
dblp:bibtexType bibtex:Incollection ;
dblp:hasSignature [ ] ;
dblp:primaryDocumentPage <https://doi.org/10.1007/978-0-387-31439-6_559> ;
dblp:pagination "815-819" ;
dblp:publishedIn "Computer Vision, A Reference Guide" ;
dblp:yearOfPublication "2014"^^<http://www.w3.org/2001/XMLSchema#gYear> ;

<https://dblp.org/rec/publi_key>
dblp:title "Publication Title." ;
dblp:bibtexType bibtex:Inproceedings ;
dblp:hasSignature [
dblp:signatureDblpName "First Author" ;
dblp:signatureCreator <https://dblp.org/pid/first_author_key> ;
], [
dblp:signatureDblpName "Second Author" ;
dblp:signatureCreator <https://dblp.org/pid/second_key> ;
] ;
dblp:primaryDocumentPage <https://my.url> ;
dblp:publishedInStream <https://dblp.org/streams/conf/hazbin> ;
dblp:pagination "42-666" ;
dblp:publishedIn "Hell" ;
dblp:yearOfPublication "2005"^^<http://www.w3.org/2001/XMLSchema#gYear> ;
"""


def _write_gz(directory, content, name="test.ttl.gz"):
    path = Path(directory) / name
    with gzip.open(path, "wt", encoding="utf8", newline="\n") as f:
        f.write(content)
    return path


def test_parse_block_valid():
    """A block with authors is parsed correctly."""
    blocks = TTL_EXAMPLE.split("\n\n")
    result = parse_block(blocks[2])
    key, title, typ, authors, url, stream, pages, venue, year = result
    assert key == "publi_key"
    assert title == "Publication Title."
    assert typ == "conference"
    assert authors == {"first_author_key": "First Author", "second_key": "Second Author"}
    assert url == "https://my.url"
    assert stream == ["conf/hazbin"]
    assert pages == "42-666"
    assert venue == "Hell"
    assert year == 2005


def test_parse_block_no_authors():
    """A block with empty signature brackets is rejected."""
    blocks = TTL_EXAMPLE.split("\n\n")
    assert parse_block(blocks[1]) is None


def test_parse_block_garbage():
    """Random text returns None."""
    assert parse_block("not a ttl block") is None


def test_publis_streamer_from_file():
    """Full pipeline: gzip file -> streamer -> parsed publications."""
    with tempfile.TemporaryDirectory() as d:
        path = _write_gz(d, TTL_EXAMPLE)
        pubs = list(publis_streamer(path))
    assert len(pubs) == 1
    assert pubs[0][0] == "publi_key"
    assert pubs[0][5] == ["conf/hazbin"]


def test_publis_streamer_missing_file():
    """A non-existent file yields nothing."""
    pubs = list(publis_streamer(Path("/nonexistent/file.ttl.gz")))
    assert pubs == []
