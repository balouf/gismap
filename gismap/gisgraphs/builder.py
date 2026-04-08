import json
import uuid

from gismap.gisgraphs.graph import lab_to_graph
from gismap.gisgraphs.groups import auto_groups, make_legend
from gismap.gisgraphs.js import default_script
from gismap.gisgraphs.options import edges as def_edges
from gismap.gisgraphs.options import interaction as def_interaction
from gismap.gisgraphs.options import nodes as def_nodes
from gismap.gisgraphs.options import physics as def_physics
from gismap.gisgraphs.style import default_style

default_vis_url = '"https://cdn.jsdelivr.net/npm/vis-network/standalone/esm/vis-network.min.js"'

gislink = '<a href="https://balouf.github.io/gismap/" target="_blank" class="watermark gislink">&copy; GisMap 2025</a>'


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
    draw_legend = kwargs.pop("draw_legend", True)
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
    legend_html = make_legend(groups, uid) if draw_legend else ""

    div = (
        f'<div class="gisgraph" id="box-{uid}">'
        f'<div id="vis-{uid}"></div>'
        f"{gislink}"
        f'<button id="redraw-{uid}" class="watermark button redraw">Redraw()</button>'
        f'<button id="fullscreen-{uid}" class="watermark button fullscreen">Full Screen</button>'
        f"{legend_html}"
        f'<div class="modal" id="modal-{uid}">'
        f'<div class="modal-content">'
        f'<span class="close" id="modal-close-{uid}">&times;</span>'
        f'<div id="modal-body-{uid}"></div>'
        f"</div></div>"
        f"</div>"
    )

    style_html = f"<style>{style.substitute(**parameters)}</style>"
    script_html = f'<script type="module">{script.substitute(**parameters)}</script>'

    return "\n".join([div, style_html, script_html])
