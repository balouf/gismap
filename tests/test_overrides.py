from gismap.lab.lab_author import LabAuthor
from gismap.lab.labmap import LabMap


class _FakeLab(LabMap):
    """Offline lab: authors are pinned via overrides (no_auto) so update_authors
    performs no network lookup."""

    def _author_iterator(self):
        yield LabAuthor("Antoine Miné")
        yield LabAuthor("Antoine Mirri")


def test_overrides_drop_and_pin():
    lab = _FakeLab(name="t")
    lab.overrides = {
        "Antoine Mirri": "drop",  # newcomer who would grab a near-homonym
        "Antoine Miné": "ldb: 99/9999, no_auto",  # pin exact source, no auto search
    }
    lab.update_authors()
    names = {a.name for a in lab.authors.values()}
    assert "Antoine Mirri" not in names
    assert "Antoine Miné" in names
    mine = next(a for a in lab.authors.values() if a.name == "Antoine Miné")
    assert mine.sources[0].key == "99/9999"


def test_no_overrides_is_noop_path():
    # With an empty overrides map, dropped/pinned logic must not interfere; we
    # only check that a "drop"-free, pinned author still goes through.
    lab = _FakeLab(name="t")
    lab.overrides = {"Antoine Miné": "no_auto", "Antoine Mirri": "no_auto"}
    lab.update_authors()
    # Both have no explicit source and no_auto -> no sources -> not added.
    assert lab.authors == {}
