import distinctipy


def auto_groups(lab, groups=None, rng=None, pastel_factor=0.3):
    if groups is None:
        groups = ego_groups
    else:
        for k, v in ego_groups.items():
            if k not in groups:
                groups[k] = v
            else:
                groups[k] = {**v, **groups[k]}
    res = {
        group: groups.get(group, {"hidden": False})
        for i, group in enumerate({a.metadata.group: None for a in lab.authors.values() if a and a.metadata.group})
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


ego_groups = {
    "star": {"display": "Star", "color": "rgb(210, 190, 70)", "hidden": False},
    "planet": {"display": "Planets", "color": "rgb(80, 120, 200)", "hidden": False},
    "moon": {"display": "Moons", "color": "rgb(140, 140, 140)", "hidden": False},
}


def make_legend(groups, uid):
    color_box_style = "width: 14px; height: 14px; display: inline-block; margin-right: 5px; vertical-align: middle;"
    entries = []
    if len(groups) > 1:
        for group_name, props in groups.items():
            color = props.get("color", "#cccccc")
            display_name = props.get("display", group_name)
            entries.append(
                f'<label class="legend-entry">'
                f'<span style="background-color: {color}; {color_box_style}"></span>'
                f'<input type="checkbox" class="legend-checkbox" data-group="{group_name}" checked="true">'
                f"{display_name}"
                f"</label>"
            )
    # Add comet checkbox
    entries.append(
        f'<label class="comet-entry">'
        f'<span style="{color_box_style}"></span>'
        f'<input type="checkbox" id="comet-{uid}">'
        f"Show Comets"
        f"</label>"
    )
    return f'<div id="legend-{uid}" class="legend">{"".join(entries)}</div>'
