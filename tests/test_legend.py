from gismap.gisgraphs.groups import _comet_color, _lighten, make_legend


def test_lighten_blends_toward_white():
    assert _lighten("rgb(80, 120, 200)") == "rgb(176, 194, 230)"


def test_lighten_passthrough_on_unknown_format():
    assert _lighten("#abcdef") == "#abcdef"


def test_comet_color_uses_lightened_planet():
    groups = {"planet": {"color": "rgb(80, 120, 200)"}}
    assert _comet_color(groups) == "rgb(176, 194, 230)"


def test_comet_color_fallback_grey():
    assert _comet_color({"team-a": {"color": "rgb(1, 2, 3)"}}) == "rgb(210, 210, 210)"


class TestMakeLegend:
    groups = {
        "planet": {
            "display": "Planets",
            "display_alt": "Members with co-publications",
            "color": "rgb(80, 120, 200)",
        },
        "moon": {
            "display": "Moons",
            "display_alt": "Most frequent collaborators",
            "color": "rgb(140, 140, 140)",
        },
    }

    def test_dual_labels_present(self):
        html = make_legend(self.groups, "uid1")
        assert 'data-default="Planets"' in html
        assert 'data-alt="Members with co-publications"' in html
        # Alternative label is exposed on hover (A4 tooltips).
        assert 'title="Members with co-publications"' in html
        assert 'data-alt="Most frequent collaborators"' in html

    def test_comet_entry_has_square_and_no_singletons(self):
        html = make_legend(self.groups, "uid1")
        assert ">Comets<" in html
        assert "(Singletons)" not in html
        # Comet square is a lightened planet color, not empty.
        assert "rgb(176, 194, 230)" in html
        assert 'data-alt="Members with no co-publications"' in html

    def test_comet_labels_can_be_overridden(self):
        html = make_legend(self.groups, "uid1", comet=("Loners", "Solo members"))
        assert 'data-default="Loners"' in html
        assert 'data-alt="Solo members"' in html

    def test_single_group_only_comet(self):
        # With a single group, only the comet entry is emitted (no group rows).
        html = make_legend({"only": {"display": "Only", "color": "rgb(1,2,3)"}}, "uid2")
        assert "comet-entry" in html
        assert 'data-default="Only"' not in html

    def test_group_without_alt_falls_back_to_display(self):
        # A group without an explicit alternative keeps its display label, so the
        # toggle is a no-op for it rather than inventing wording.
        html = make_legend({"a": {"display": "Team A", "color": "rgb(1,2,3)"}, "b": {"color": "rgb(4,5,6)"}}, "u")
        assert 'data-default="Team A"' in html
        assert 'data-alt="Team A"' in html
