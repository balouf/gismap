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

    nodes, edges, publications = lab_to_graph(lab)

    # Embed JSON inside <script>: a literal "</" anywhere in the data
    # (e.g. "</script>" inside a pub title) would terminate the host
    # <script> tag. JSON allows the alternative spelling "<\/", which
    # parses identically and is inert as HTML.
    def _embed(obj):
        return json.dumps(obj).replace("</", "<\\/")

    parameters = {
        "vis_url": vis_url,
        "uid": uid,
        "nodes": _embed(nodes),
        "edges": _embed(edges),
        "publications": _embed(publications),
        "options": _embed(options),
        "lab_name": _embed(lab.name or "gismap"),
    }
    legend_html = make_legend(groups, uid) if draw_legend else ""

    # Inline SVGs for the bottom-right fullscreen icon. CSS toggles which
    # one is shown via the :fullscreen pseudo-class on box-$uid.
    expand_svg = (
        '<svg class="fs-expand" viewBox="0 0 18 18" width="16" height="16" fill="none"'
        ' stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"'
        ' aria-hidden="true">'
        '<polyline points="3,7 3,3 7,3"/>'
        '<polyline points="11,3 15,3 15,7"/>'
        '<polyline points="15,11 15,15 11,15"/>'
        '<polyline points="7,15 3,15 3,11"/>'
        "</svg>"
    )
    compress_svg = (
        '<svg class="fs-compress" viewBox="0 0 18 18" width="16" height="16" fill="none"'
        ' stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"'
        ' aria-hidden="true">'
        '<polyline points="7,3 7,7 3,7"/>'
        '<polyline points="15,7 11,7 11,3"/>'
        '<polyline points="11,15 11,11 15,11"/>'
        '<polyline points="3,11 7,11 7,15"/>'
        "</svg>"
    )

    menu_button_attrs = 'class="watermark button menu" aria-label="Menu" aria-haspopup="true" aria-expanded="false"'
    fs_icon_attrs = (
        'viewBox="0 0 18 18" width="14" height="14" fill="none"'
        ' stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"'
        ' aria-hidden="true"'
    )
    fs_menu_icon = (
        f'<svg class="menu-icon fs-expand" {fs_icon_attrs}>'
        '<polyline points="3,7 3,3 7,3"/>'
        '<polyline points="11,3 15,3 15,7"/>'
        '<polyline points="15,11 15,15 11,15"/>'
        '<polyline points="7,15 3,15 3,11"/>'
        "</svg>"
        f'<svg class="menu-icon fs-compress" {fs_icon_attrs}>'
        '<polyline points="7,3 7,7 3,7"/>'
        '<polyline points="15,7 11,7 11,3"/>'
        '<polyline points="11,15 11,11 15,11"/>'
        '<polyline points="3,11 7,11 7,15"/>'
        "</svg>"
    )
    menu_item_template = (
        '<li role="none"><a href="#" role="menuitem" class="menu-item" data-action="{a}">'
        '<span class="menu-label">{label}</span>{icon}'
        "</a></li>"
    )
    menu_entries = "".join(
        menu_item_template.format(a=a, label=label, icon=icon)
        for a, label, icon in [
            ("redraw", "Redraw", ""),
            ("fullscreen", "Full Screen", fs_menu_icon),
            ("toggle-legend", "Hide Legend", ""),
            ("dl-bib", "Download lab.bib", ""),
            ("dl-png", "Download PNG", ""),
            ("copy-png", "Copy PNG to clipboard", ""),
        ]
    )
    menu_html = (
        f'<div class="menu-wrap" id="menu-wrap-{uid}">'
        f'<button id="menu-{uid}" {menu_button_attrs}>'
        '<svg viewBox="0 0 18 18" width="16" height="16" fill="none" stroke="currentColor"'
        ' stroke-width="1.8" stroke-linecap="round" aria-hidden="true">'
        '<line x1="3" y1="5" x2="15" y2="5"/>'
        '<line x1="3" y1="9" x2="15" y2="9"/>'
        '<line x1="3" y1="13" x2="15" y2="13"/>'
        "</svg>"
        "</button>"
        f'<ul id="menu-list-{uid}" class="menu-list" role="menu" hidden>'
        f"{menu_entries}"
        "</ul>"
        "</div>"
    )

    fs_button_attrs = 'class="watermark button fullscreen" title="Full Screen" aria-label="Full Screen"'
    fs_button_html = f'<button id="fullscreen-{uid}" {fs_button_attrs}>{expand_svg}{compress_svg}</button>'

    div = (
        f'<div class="gisgraph" id="box-{uid}">'
        f'<div id="vis-{uid}"></div>'
        f"{gislink}"
        f"{menu_html}"
        f"{fs_button_html}"
        f"{legend_html}"
        f'<div class="modal" id="modal-{uid}">'
        f'<div class="modal-content">'
        f'<div class="modal-header">'
        f'<div class="modal-title" id="modal-title-{uid}"></div>'
        f'<div class="modal-actions" id="modal-actions-{uid}"></div>'
        f'<span class="close" id="modal-close-{uid}" role="button" tabindex="0" aria-label="Close">&times;</span>'
        f"</div>"
        f'<div id="modal-body-{uid}"></div>'
        f"</div></div>"
        f"</div>"
    )

    style_html = f"<style>{style.substitute(**parameters)}</style>"
    script_html = f'<script type="module">{script.substitute(**parameters)}</script>'

    return "\n".join([div, style_html, script_html])
