import json
import uuid
from domonic import tags

from gismap.gisgraphs.graph import lab_to_graph
from gismap.gisgraphs.groups import auto_groups
from gismap.gisgraphs.options import (
    physics as def_physics,
    nodes as def_nodes,
    edges as def_edges,
    interaction as def_interaction,
)
from gismap.gisgraphs.style import default_style
from gismap.gisgraphs.js import default_script
from gismap.gisgraphs.groups import make_legend


default_vis_url = '"https://unpkg.com/vis-network/standalone/esm/vis-network.min.js"'

gislink = tags.a(
    "&copy; GisMap 2025",
    _href="https://balouf.github.io/gismap/",
    _target="_blank",
    _class="watermark gislink",
)


def make_vis(lab, **kwargs):
    """
    Generate HTML visualization of a lab's collaboration network.

    Parameters
    ----------
    lab: :class:`~gismap.lab.labmap.LabMap`
        Lab to display.
    uid: :class:`str`, optional
        Unique identifier for DOM elements. Auto-generated if not provided.
    vis_url: :class:`str`, optional
        URL to vis-network library.
    groups: :class:`dict`, optional
        Group styling configuration.
    draw_legend: :class:`bool`, optional
        Whether to draw the legend. Defaults to True if multiple groups.
    physics: :class:`dict`, optional
        Physics engine configuration.
    nodes_options: :class:`dict`, optional
        Node styling options.
    edges_options: :class:`dict`, optional
        Edge styling options.
    interaction_options: :class:`dict`, optional
        Interaction settings.
    style: :class:`string.Template`, optional
        CSS template.
    script: :class:`string.Template`, optional
        JavaScript template.

    Returns
    -------
    :class:`str`
        HTML code as a string.
    """
    uid = kwargs.pop("uid", None)
    if uid is None:
        uid = str(uuid.uuid4())[:8]
    vis_url = kwargs.pop("vis_url", default_vis_url)
    groups = kwargs.pop("groups", None)
    groups = auto_groups(lab, groups)
    draw_legend = kwargs.pop("draw_legend", len(groups) > 1)
    physics = kwargs.pop("physics", def_physics)
    nodes_options = kwargs.pop("nodes_options", def_nodes)
    edges_options = kwargs.pop("edges_options", def_edges)
    interaction_options = kwargs.pop("interaction_option", def_interaction)
    options = {
        "physics": physics,
        "groups": groups,
        "nodes": nodes_options,
        "edges": edges_options,
        "interaction": interaction_options,
    }
    style = kwargs.pop("style", default_style)
    script = kwargs.pop("script", default_script)
    if kwargs:
        raise TypeError(f"unexpected keyword arguments: {repr(kwargs)}")

    nodes, edges = lab_to_graph(lab)

    parameters = {
        "vis_url": vis_url,
        "uid": uid,
        "nodes": json.dumps(nodes),
        "edges": json.dumps(edges),
        "options": json.dumps(options),
    }
    div = tags.div(_class="gisgraph", _id=f"box-{uid}")
    div.appendChild(tags.div(_id=f"vis-{uid}"))
    div.appendChild(gislink)
    div.appendChild(
        tags.button("Redraw()", _id=f"redraw-{uid}", _class="watermark button redraw")
    )
    div.appendChild(
        tags.button(
            "Full Screen", _id=f"fullscreen-{uid}", _class="watermark button fullscreen"
        )
    )
    comets = not all(n.get("connected") for n in nodes)
    if draw_legend or comets:
        div.appendChild(make_legend(groups, uid))
    modal = tags.div(_class="modal", _id=f"modal-{uid}")
    modal_content = tags.div(_class="modal-content")
    modal_content.appendChild(
        tags.span("&times;", _class="close", _id=f"modal-close-{uid}")
    )
    modal_content.appendChild(tags.div(_id=f"modal-body-{uid}"))
    modal.appendChild(modal_content)
    div.appendChild(modal)

    style = tags.style(style.substitute(**parameters))
    script = tags.script(script.substitute(**parameters), _type="module")

    return "\n".join(f"{content}" for content in [div, style, script])
