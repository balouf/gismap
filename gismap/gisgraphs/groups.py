import re
from html import escape

import distinctipy

# Two label sets for the special ego groups. Each group ships a primary
# ("display") and an alternative ("display_alt") label: the legend shows one and
# exposes the other on hover, and a menu entry swaps which one is visible. Both
# are fully overridable per group via the ``groups=`` argument of make_vis, so a
# lab can use wording unrelated to astronomy.
#
# EgoMaps get people-centric wording (planets are *your* co-authors); other labs
# get membership-centric wording (planets are members with co-publications).
ego_groups = {
    "star": {"display": "Star", "display_alt": "Central researcher", "color": "rgb(210, 190, 70)", "hidden": False},
    "planet": {"display": "Planets", "display_alt": "Co-authors", "color": "rgb(80, 120, 200)", "hidden": False},
    "moon": {
        "display": "Moons",
        "display_alt": "Most frequent collaborators",
        "color": "rgb(140, 140, 140)",
        "hidden": False,
    },
}

base_groups = {
    "star": {"display": "Star", "display_alt": "Central researcher", "color": "rgb(210, 190, 70)", "hidden": False},
    "planet": {
        "display": "Planets",
        "display_alt": "Members with co-publications",
        "color": "rgb(80, 120, 200)",
        "hidden": False,
    },
    "moon": {
        "display": "Moons",
        "display_alt": "Most frequent collaborators",
        "color": "rgb(140, 140, 140)",
        "hidden": False,
    },
}

# Comet entry (members with no co-publication): a single generic legend row
# built directly in make_legend (comets can belong to any group). (display, alt)
ego_comet = ("Comets", "Co-authors with no shared publication")
base_comet = ("Comets", "Members with no co-publications")


def is_ego(lab):
    """True when ``lab`` is an EgoMap (checked by name to avoid a circular import)."""
    return any(c.__name__ == "EgoMap" for c in type(lab).__mro__)


def auto_groups(lab, groups=None, rng=None, pastel_factor=0.3):
    defaults = ego_groups if is_ego(lab) else base_groups
    if groups is None:
        groups = defaults
    else:
        for k, v in defaults.items():
            if k not in groups:
                groups[k] = v
            else:
                groups[k] = {**v, **groups[k]}
    res = {
        group: groups.get(group, {"hidden": False})
        for group in {a.metadata.group: None for a in lab.authors.values() if a and a.metadata.group}
    }
    n_colors = len([None for g in res.values() if "color" not in g])
    colors = distinctipy.get_colors(n_colors, pastel_factor=pastel_factor, rng=rng)
    colors = [f"rgb({int(r * 255)},{int(g * 255)},{int(b * 255)})" for r, g, b in colors]
    i = 0
    for group in res.values():
        if "color" not in group:
            group["color"] = colors[i]
            i += 1
    return res


def _lighten(color, factor=0.55):
    """Blend an ``rgb(r, g, b)`` string toward white. Returns it unchanged if
    it is not in that exact form."""
    m = re.fullmatch(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", color)
    if not m:
        return color
    r, g, b = (int(c + (255 - c) * factor) for c in map(int, m.groups()))
    return f"rgb({r}, {g}, {b})"


def _comet_color(groups):
    """A lighter shade for the comet square: lightened member (planet) color
    when there is one, neutral light grey otherwise."""
    planet = groups.get("planet")
    base = planet.get("color") if planet else None
    return _lighten(base) if base else "rgb(210, 210, 210)"


def _entry(display, alt, color, checkbox_html, *, cls="legend-entry", extra_attrs=""):
    """One legend row. The primary label is the visible text node (kept a
    *direct* child so the canvas PNG export can read it); the alternative label
    is exposed via ``title`` and both are stored as data-attributes for the
    default/alternative labels toggle."""
    color_box_style = "width: 14px; height: 14px; display: inline-block; margin-right: 5px; vertical-align: middle;"
    return (
        f'<label class="{cls}" data-default="{escape(display, quote=True)}"'
        f' data-alt="{escape(alt, quote=True)}" title="{escape(alt, quote=True)}"{extra_attrs}>'
        f'<span style="background-color: {color}; {color_box_style}"></span>'
        f"{checkbox_html}"
        f"{escape(display)}"
        f"</label>"
    )


def make_legend(groups, uid, comet=base_comet):
    entries = []
    if len(groups) > 1:
        for group_name, props in groups.items():
            color = props.get("color", "#cccccc")
            display = props.get("display", group_name)
            alt = props.get("display_alt") or display
            gid = escape(group_name, quote=True)
            checkbox = f'<input type="checkbox" class="legend-checkbox" data-group="{gid}" checked="true">'
            entries.append(_entry(display, alt, color, checkbox))
    # Comet entry (hidden by default, JS reveals it if singletons exist).
    comet_display, comet_alt = comet
    comet_checkbox = f'<input type="checkbox" id="comet-{uid}">'
    entries.append(
        _entry(
            comet_display,
            comet_alt,
            _comet_color(groups),
            comet_checkbox,
            cls="legend-entry comet-entry",
            extra_attrs=f' id="comet-entry-{uid}" style="display:none"',
        )
    )
    return f'<div id="legend-{uid}" class="legend">{"".join(entries)}</div>'
