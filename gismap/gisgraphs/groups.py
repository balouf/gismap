from domonic import tags
import distinctipy
import colorsys


# def colors(i, s=0.65, l=0.55):
#     """
#     Creates deterministic colors. AI-coded.
#
#     Parameters
#     ----------
#     i: :class:`int`
#         Color number.
#     s: :class:`float`
#         Saturation.
#     l: :class:`float`
#         Lightness.
#
#     Returns
#     -------
#     :class:`str`
#         Color string.
#     """
#     # Use "golden angle" to make nice evolution (not i * 360/N)
#     golden_angle = 137.508  # recommended by AI
#     h = (200 + (i * golden_angle) % 360) / 360.0
#     r, g, b = colorsys.hls_to_rgb(h, l, s)
#     return '#{0:02x}{1:02x}{2:02x}'.format(int(r * 255), int(g * 255), int(b * 255))


def auto_groups(lab, groups=None, rng=None, pastel_factor=.3):
    if groups is None:
        groups = ego_groups
    else:
        for k, v in ego_groups.items():
            if k not in groups:
                groups[k] = v
            else:
                groups[k] = {**v, **groups[k]}
    res = {group: groups.get(group, {'hidden': False}) for i, group in
           enumerate({a.metadata.group: None for a in lab.authors.values() if a and a.metadata.group})
           }
    n_colors = len([None for g in res.values() if 'color' not in g])
    colors = distinctipy.get_colors(n_colors, pastel_factor=pastel_factor, rng=rng)
    colors = [f"rgb({int(r * 255)},{int(g * 255)},{int(b * 255)})" for r, g, b in colors]
    i = 0
    for group in res.values():
        if 'color' not in group:
            group['color'] = colors[i]
            i += 1
    return res


ego_groups = {'star': {'display': "Star", "color": "rgb(210, 190, 70)", "hidden": False},
              'planet': {'display': "Planets", "color": "rgb(59, 101, 178)", "hidden": False},
              'moon': {'display': 'Moons', "color": "rgb(140, 140, 140)", "hidden": False}}


def make_legend(groups, uid):
    legend = tags.div(_id=f"legend-{uid}", _class="legend")
    if len(groups) > 1:
        for group_name, props in groups.items():
            color = props.get("color", "#cccccc")
            display_name = props.get("display", group_name)
            entry = tags.label(display_name, _class="legend-entry")
            entry.appendChild(
                tags.input(**{"type": "checkbox", "class": "legend-checkbox", "data-group": group_name}, checked=True))
            entry.appendChild(tags.span(
                _style=f"background-color: {color}; width: 14px; height: 14px; display: inline-block; margin-right: 5px; vertical-align: middle;"))
            legend.appendChild(entry)
    entry = tags.label("Show Comets", _class="comet-entry")
    entry.appendChild(tags.input(**{"type": "checkbox", "id": f"comet-{uid}"}))
    legend.appendChild(entry)
    return legend
