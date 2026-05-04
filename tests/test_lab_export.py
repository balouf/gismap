"""Smoke tests for LabMap export methods (to_bib / to_json / to_csv)."""

import json

import pytest

from gismap.lab.lab_author import AuthorMetadata, LabAuthor
from gismap.lab.labmap import LabMap
from gismap.sources.hal import HALAuthor, HALPublication
from gismap.sources.multi import SourcedPublication


@pytest.fixture
def tiny_lab():
    lab = LabMap(name="tiny")
    hal_a = HALAuthor(name="Alice Smith", key="alice-smith")
    hal_b = HALAuthor(name="Bob Jones", key="bob-jones")
    a = LabAuthor(name="Alice Smith", sources=[hal_a], metadata=AuthorMetadata(group="lab"))
    b = LabAuthor(name="Bob Jones", sources=[hal_b], metadata=AuthorMetadata(group="lab"))
    lab.authors = {a.key: a, b.key: b}

    hal_pub = HALPublication(
        title="A Joint Paper",
        authors=[a, b],
        venue="ICML",
        type="conference",
        year=2024,
        key="hal-1234",
        metadata={"url": "https://hal.science/hal-1234", "abstract": "Some abstract."},
    )
    sp = SourcedPublication.from_sources([hal_pub])
    lab.publications = {sp.key: sp}
    return lab


def test_to_bib_writes_file(tiny_lab, tmp_path):
    path = tmp_path / "tiny"
    tiny_lab.to_bib(name=str(path))
    bib = (tmp_path / "tiny.bib").read_text(encoding="utf8")
    assert bib.startswith("@inproceedings{hal-1234,")
    assert "abstract = {Some abstract.}" in bib


def test_to_bib_uses_lab_name_by_default(tiny_lab, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tiny_lab.to_bib()
    assert (tmp_path / "tiny.bib").exists()


def test_to_bib_query_filters(tiny_lab, tmp_path):
    path = tmp_path / "tiny"
    tiny_lab.to_bib(name=str(path), query=lambda p: p.year < 2000)
    bib = (tmp_path / "tiny.bib").read_text(encoding="utf8")
    assert bib.strip() == ""


def test_to_json_valid(tiny_lab, tmp_path):
    path = tmp_path / "tiny"
    tiny_lab.to_json(name=str(path))
    data = json.loads((tmp_path / "tiny.json").read_text(encoding="utf8"))
    assert data["name"] == "tiny"
    assert len(data["authors"]) == 2
    assert len(data["publications"]) == 1
    pub = data["publications"][0]
    assert pub["title"] == "A Joint Paper"
    assert pub["year"] == 2024
    assert pub["sources"][0]["db_name"] == "hal"


def test_to_csv_two_files(tiny_lab, tmp_path):
    path = tmp_path / "tiny"
    tiny_lab.to_csv(name=str(path))
    authors_csv = (tmp_path / "tiny_authors.csv").read_text(encoding="utf8")
    pubs_csv = (tmp_path / "tiny_publications.csv").read_text(encoding="utf8")
    assert "Alice Smith" in authors_csv
    assert "Bob Jones" in authors_csv
    assert "A Joint Paper" in pubs_csv
    assert "Alice Smith|Bob Jones" in pubs_csv
    assert authors_csv.startswith("key,name,group,url,sources")
    assert pubs_csv.startswith("cite_key,title,year,type,venue,authors,primary_url,abstract,other_urls")


def test_to_bib_raises_when_no_name():
    lab = LabMap()
    lab.authors = {}
    lab.publications = {}
    with pytest.raises(ValueError):
        lab.to_bib()


def test_save_html_raises_when_no_name():
    lab = LabMap()
    with pytest.raises(ValueError):
        lab.save_html()
