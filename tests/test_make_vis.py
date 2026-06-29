"""Offline regression tests for the HTML/JS visualization layer.

The collaboration-graph renderer grew a lot in 0.6.0 (slider, theme, legend
label toggle, comet gravity, smart initials...). None of it touches the network,
so we build a synthetic lab from the manual backend and assert on the generated
HTML. This guards the JS/CSS templates against silent regressions.
"""

import pytest

from gismap.gisgraphs.js import default_script
from gismap.gisgraphs.style import default_style
from gismap.lab.lab_author import LabAuthor
from gismap.lab.labmap import ListMap


def _build_lab():
    """A small lab covering every display case (planets, a moon, a comet,
    composite first name, shared initials), built entirely offline by passing
    LabAuthor objects (with explicit sources) to add_publication."""
    lab = ListMap([], name="Test Lab")
    lab.authors = {}
    lab.publications = {}

    def mk(name, key, group):
        a = LabAuthor(f"{name} (ldb: {key})")
        a.metadata.group = group
        return a

    authors = [
        mk("Alice Smith", "alice", "planet"),
        mk("Jérôme Lang", "jl1", "planet"),  # JLa
        mk("Julien Lesca", "jl2", "planet"),  # JLe
        mk("Jean-François Laslier", "jfl", "planet"),  # JFL
        mk("Bob External", "bob", "moon"),
        mk("Lonely Member", "lonely", "planet"),  # no co-pub -> comet
    ]
    lab.authors = {a.key: a for a in authors}

    def add(title, who, year):
        lab.add_publication(title=title, authors=[lab.authors[k] for k in who], venue="JAIR", year=year)

    add("Voting and social choice", ["alice", "jl1", "jfl"], 2015)
    add("Strategic candidacy in elections", ["jl1", "jl2"], 2019)
    add("Fair division revisited", ["alice", "bob"], 2022)
    return lab


@pytest.fixture(scope="module")
def lab():
    return _build_lab()


@pytest.fixture(scope="module")
def html(lab):
    return lab.html()


def test_templates_substitute_without_error():
    # Guards against a stray "$" sneaking into the JS/CSS templates.
    params = dict(
        vis_url='"x"',
        uid="u",
        nodes="[]",
        edges="[]",
        publications="{}",
        options='{"groups":{}}',
        lab_name='"Demo"',
        theme='"auto"',
    )
    assert default_script.substitute(**params)
    assert default_style.substitute(**params)


class TestInitials:
    def test_composite_first_name(self, html):
        assert '"JFL"' in html

    def test_disambiguated_shared_initials(self, html):
        assert '"JLa"' in html
        assert '"JLe"' in html


class TestNodes:
    def test_minimum_width_constraint(self, html):
        assert '"widthConstraint"' in html
        assert '"minimum": 34' in html

    def test_options_merge_keeps_defaults(self, lab):
        # A partial nodes_options overrides one field but keeps the rest.
        html = lab.html(nodes_options={"widthConstraint": {"minimum": 99}})
        assert '"minimum": 99' in html
        assert '"shape": "circle"' in html  # default preserved by the merge


class TestLegend:
    def test_dual_labels_and_tooltip(self, html):
        assert 'data-default="Planets"' in html
        assert 'data-alt="Members with co-publications"' in html
        assert 'title="Members with co-publications"' in html

    def test_comet_entry_square_and_no_singletons(self, html):
        assert "comet-entry" in html
        assert ">Comets<" in html
        assert "(Singletons)" not in html

    def test_legend_mode_toggle(self, html):
        assert 'data-action="legend-mode"' in html
        assert "Use alternative labels" in html

    def test_exhaustive_wording(self, lab):
        # Default (unknown truncation) -> "Most frequent collaborators".
        assert "Most frequent collaborators" in lab.html()
        # Known-complete moon set -> plain "Collaborators".
        lab._group_truncated = {"moon": False}
        html = lab.html()
        assert 'data-alt="Collaborators"' in html
        assert "Most frequent collaborators" not in html
        lab._group_truncated = {}  # restore for other tests


class TestTimeFilter:
    def test_slider_and_empty_state(self, html):
        assert 'data-action="time-filter"' in html
        assert 'id="slider-min-' in html
        assert 'id="slider-max-' in html
        assert 'class="empty-graph"' in html


class TestCometGravity:
    def test_attractor_builder_present(self, html):
        assert "buildCometAttractors" in html


class TestTheme:
    def test_default_auto(self, html):
        assert 'data-action="theme"' in html
        assert "cycleTheme" in html
        assert 'let themeMode = "auto"' in html
        assert "gm-dark" in html  # forced-theme CSS shipped

    def test_theme_kwarg(self, lab):
        assert 'let themeMode = "dark"' in lab.html(theme="dark")


class TestBibExport:
    def test_bib_download_excludes_copy_button(self, html):
        # Regression guard: the modal .bib download/copy must read the <pre> via
        # bibText() (text nodes only), never p.textContent — which would include
        # the appended "Copy" button and break the BibTeX.
        assert "function bibText(pre)" in html
        assert ".map(bibText)" in html
        assert "writeText(bibText(pre))" in html
        assert "p => p.textContent" not in html

    def test_interaction_options_kwarg_accepted(self, lab):
        # Documented plural name must not raise (used to be silently rejected).
        assert lab.html(interaction_options={"hover": False})
        assert lab.html(interaction_option={"hover": False})  # historical name still works
