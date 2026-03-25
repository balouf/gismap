from domonic import tags
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
        for i, group in enumerate(
            {
                a.metadata.group: None
                for a in lab.authors.values()
                if a and a.metadata.group
            }
        )
    }
    n_colors = len([None for g in res.values() if "color" not in g])
    colors = distinctipy.get_colors(n_colors, pastel_factor=pastel_factor, rng=rng)
    colors = [
        f"rgb({int(r * 255)},{int(g * 255)},{int(b * 255)})" for r, g, b in colors
    ]
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
    legend = tags.div(_id=f"legend-{uid}", _class="legend")
    if len(groups) > 1:
        for group_name, props in groups.items():
            color = props.get("color", "#cccccc")
            display_name = props.get("display", group_name)
            color_box = tags.span(
                    _style=f"background-color: {color}; width: 14px; height: 14px; display: inline-block; margin-right: 5px; vertical-align: middle;"
            )
            check_box = tags.input(
                    **{
                        "type": "checkbox",
                        "class": "legend-checkbox",
                        "data-group": group_name,
                    },
                    checked=True,
                )
            entry = tags.label(color_box, _class="legend-entry")
            entry.appendChild(check_box)
            entry.appendChild(display_name)
            legend.appendChild(entry)
    # Add comet checkbox
    empty_box = tags.span(
            _style="width: 14px; height: 14px; display: inline-block; margin-right: 5px; vertical-align: middle;"
    )
    comet_check = tags.input(**{"type": "checkbox", "id": f"comet-{uid}"})
    entry = tags.label(empty_box, _class="comet-entry")
    entry.appendChild(comet_check)
    entry.appendChild("Show Comets")
    legend.appendChild(entry)
    return legend
