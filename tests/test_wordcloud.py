import pytest

from gismap.gismo import GismoLab, WordCloud, publication_text
from gismap.lab.lab_author import LabAuthor
from gismap.lab.labmap import ListMap


def _build_lab():
    """Offline keyword-rich lab (two groups), built via the manual backend."""
    lab = ListMap([], name="WC Lab")
    lab.authors = {}
    lab.publications = {}

    def mk(name, key, group):
        a = LabAuthor(f"{name} (ldb: {key})")
        a.metadata.group = group
        return a

    authors = [mk("Alice Smith", "alice", "teamA"), mk("Bob Jones", "bob", "teamA"), mk("Carol Lee", "carol", "teamB")]
    lab.authors = {a.key: a for a in authors}

    def add(title, who):
        lab.add_publication(title=title, authors=[lab.authors[k] for k in who], venue="V", year=2020)

    add("graph routing in wireless networks", ["alice", "bob"])
    add("wireless sensor networks scheduling", ["alice", "bob"])
    add("distributed graph algorithms for networks", ["alice"])
    add("energy efficient wireless networks", ["bob"])
    add("optimal transport and machine learning", ["carol"])
    add("machine learning for optimal transport", ["carol"])
    return lab


@pytest.fixture(scope="module")
def lab():
    return _build_lab()


def test_publication_text_is_title_without_abstract():
    lab = _build_lab()
    p = next(iter(lab.publications.values()))
    assert publication_text(p) == p.title


class TestKeywords:
    def test_topic_query_surfaces_relevant_words(self, lab):
        words = lab.keywords("networks", k=20)
        assert words
        assert all(isinstance(w, tuple) and len(w) == 2 for w in words)
        assert "network" in " ".join(w for w, _ in words)

    def test_group_query(self, lab):
        assert lab.keywords(group="teamA", k=20)
        assert lab.keywords(group="does-not-exist") == []

    def test_gismo_lab_is_reusable(self, lab):
        gl = lab.gismo_lab()
        assert isinstance(gl, GismoLab)
        assert gl.keywords("graph", k=10)
        assert gl.keywords(group="teamB", k=10)  # reuse without rebuilding


class TestWordCloud:
    def test_wordcloud_renders_html(self, lab):
        wc = lab.wordcloud("networks", k=15)
        assert isinstance(wc, WordCloud)
        html = wc.to_html()
        assert "gismap-wordcloud" in html
        assert "<span" in html
        assert wc._repr_html_() == html

    def test_empty_wordcloud(self):
        wc = WordCloud([], title="nothing")
        assert "No keywords" in wc.to_html()
