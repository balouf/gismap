from string import Template

# language=javascript
draw_script = """
import { DataSet, Network } from $vis_url;

const nodes = new DataSet($nodes);
const edges = new DataSet($edges);
const publications = $publications;
const options = $options;
const labName = $lab_name;
const container = document.getElementById('vis-$uid');
let hoveredEdgeId = null;
let hoveredNodeId = null;
let currentNetwork = null;
let lastHasSingletons = false;
// null = follow auto rule (multi-group OR singletons present);
// true/false = user override from the menu.
let legendVisibilityOverride = null;
// null = no time filtering; [minYear, maxYear] = keep only collaborations with
// at least one publication in that (inclusive) range. Driven by the slider.
let yearRange = null;

// ----- Modal rendering helpers (fed by the shared `publications` dict) -----

function escapeHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function safeFilename(s) {
    // Preserve UTF-8 (accents, etc.); only strip filesystem-hostile chars
    // (Windows-forbidden + control chars) and collapse whitespace.
    const cleaned = String(s)
        .replace(/[\\\\\\/:*?"<>|\\x00-\\x1f]/g, '_')
        .replace(/\\s+/g, '_')
        .replace(/^[._]+|[._]+$$/g, '');
    return cleaned || 'publications';
}

function linkifyAuthor(a) {
    const name = escapeHtml(a.name || 'Unknown Author');
    if (a.url) {
        return '<a href="' + escapeHtml(a.url) + '" target="_blank">' + name + '</a>';
    }
    return '<span>' + name + '</span>';
}

function formatAuthors(authors) {
    if (!authors || authors.length === 0) return '';
    if (authors.length === 1) return linkifyAuthor(authors[0]);
    if (authors.length === 2) return linkifyAuthor(authors[0]) + ' and ' + linkifyAuthor(authors[1]);
    const head = authors.slice(0, -1).map(linkifyAuthor).join(', ');
    return head + ', and ' + linkifyAuthor(authors[authors.length - 1]);
}

function renderPub(pub) {
    const titleHtml = pub.url
        ? '<a href="' + escapeHtml(pub.url) + '" target="_blank">' + escapeHtml(pub.title) + '</a>'
        : '<span>' + escapeHtml(pub.title) + '</span>';
    const authorsHtml = formatAuthors(pub.authors);
    const venue = escapeHtml(pub.venue || '');
    const year = escapeHtml(pub.year != null ? pub.year : '');
    const parts = [
        '<div class="pub">' + titleHtml + ', by <i>' + authorsHtml + '</i>. ' + venue + ', ' + year + '.',
        ' <a href="#" class="bib-toggle">.bib</a>',
    ];
    if (pub.abstract) parts.push(' <a href="#" class="abs-toggle">abstract</a>');
    parts.push('<pre class="bib" hidden>' + escapeHtml(pub.bib || '') + '</pre>');
    if (pub.abstract) parts.push('<pre class="abs" hidden>' + escapeHtml(pub.abstract) + '</pre>');
    parts.push('</div>');
    return parts.join('');
}

function renderPubListBody(pubKeys, n) {
    if (n == null) n = 10;
    const keys = pubKeys || [];
    const lis = keys.map((k, i) => {
        const pub = publications[k];
        if (!pub) return '';
        const cls = i < n ? '' : ' class="extra-publication" style="display:none;"';
        return '<li' + cls + '>' + renderPub(pub) + '</li>';
    });
    if (keys.length > n) {
        lis.push('<li><a href="#" class="show-more">Show more…</a></li>');
    }
    return '<div class="pub-list"><ul>' + lis.join('') + '</ul></div>';
}

function renderActions(downloadName) {
    const fname = escapeHtml(safeFilename(downloadName));
    return '<a href="#" class="dl-all-bib" data-name="' + fname + '">Download .bib</a>';
}

// Read a <pre class="bib"> without its appended copy button: that button lives
// inside the <pre>, so pre.textContent would otherwise leak "Copy"/"Copied!"
// into the BibTeX and break parsing. We keep only the direct text nodes.
function bibText(pre) {
    let s = '';
    pre.childNodes.forEach(n => { if (n.nodeType === Node.TEXT_NODE) s += n.textContent; });
    return s;
}

function openModal(titleHtml, pubKeys, downloadName) {
    document.getElementById('modal-title-$uid').innerHTML = titleHtml;
    document.getElementById('modal-actions-$uid').innerHTML = renderActions(downloadName);
    document.getElementById('modal-body-$uid').innerHTML = renderPubListBody(pubKeys);
    document.getElementById('modal-$uid').style.display = "block";
}

function nodeTitleHtml(node) {
    return 'Publications of ' + linkifyAuthor({name: node.name, url: node.url});
}

function edgeTitleHtml(a, b) {
    return 'Joint publications from ' + linkifyAuthor({name: a.name, url: a.url})
        + ' and ' + linkifyAuthor({name: b.name, url: b.url});
}

// An edge survives the time filter if any of its publications falls in range.
function edgeInYearRange(edge) {
    if (!yearRange) return true;
    const [lo, hi] = yearRange;
    return (edge.pub_keys || []).some(k => {
        const y = publications[k]?.year;
        return y != null && y >= lo && y <= hi;
    });
}

// ----- Get the group color and position of a node (gradient edges) -----
function getNodeInfos(network, node) {
    if (node && !options.groups?.[node.group]?.hidden) {
        return [options.groups[node.group]?.color, network.getPositions([node.id])[node.id]]
    }
    return [false, false];
}

// Comet gravity (gentle, physics-based). Build invisible "attractor" spring
// edges from each shown comet to a representative node of its own group, so
// same-colour comets drift toward same-colour clusters while staying free to
// move and be dragged. These edges live only in the rendered network, never in
// the `edges` data model, so the singleton/comet detection above is untouched.
// `attractor:true` flags them so clicks/gradients ignore them.
function buildCometAttractors(visibleNodes, visibleEdges, connectedIds) {
    const comets = visibleNodes.get().filter(n => !connectedIds.has(n.id));
    if (!comets.length) return [];
    // Pick the highest-degree connected node per group as the cluster anchor.
    const degree = {};
    visibleEdges.forEach(e => {
        degree[e.from] = (degree[e.from] || 0) + 1;
        degree[e.to] = (degree[e.to] || 0) + 1;
    });
    const anchor = {};
    visibleNodes.get().forEach(n => {
        if (!connectedIds.has(n.id)) return;
        if (!(n.group in anchor) || (degree[n.id] || 0) > (degree[anchor[n.group]] || 0)) anchor[n.group] = n.id;
    });
    const attractors = [];
    comets.forEach(c => {
        const target = anchor[c.group];
        if (target != null && target !== c.id) {
            attractors.push({
                id: 'attractor-' + c.id, from: c.id, to: target, attractor: true,
                // Transparent in every state: vis repaints connected edges with
                // the hover/highlight colour when a node is hovered/selected.
                color: {color: 'rgba(0,0,0,0)', hover: 'rgba(0,0,0,0)',
                    highlight: 'rgba(0,0,0,0)', inherit: false},
                width: 0.5, hoverWidth: 0, selectionWidth: 0, length: 320, smooth: false,
            });
        }
    });
    return attractors;
}


// main course
function draw_graph() {
    // No clean redraw so far, so we re-create everything :(
    // Set hidden groups according to legend, if any
    document.querySelectorAll('#legend-$uid .legend-checkbox').forEach(cb => {
    const group = cb.getAttribute('data-group');
    options.groups[group].hidden = !cb.checked;
        });


    // First compute the nodes to display.
    var visibleNodes = new DataSet(nodes.get({
      filter: node => !options.groups?.[node.group]?.hidden}));
    var visibleNodeIds = new Set(visibleNodes.map(node => node.id));
    // Reduce edges (group visibility + optional time-window filter)
    const visibleEdges = new DataSet(edges.get({
        filter: edge => visibleNodeIds.has(edge.from) && visibleNodeIds.has(edge.to)
            && edgeInYearRange(edge)}));
    // Detect singletons: nodes with no visible edges
    const connectedIds = new Set();
    visibleEdges.forEach(edge => {
        connectedIds.add(edge.from);
        connectedIds.add(edge.to);
    });
    const hasSingletons = visibleNodes.length > connectedIds.size;

    // Show/hide the comet checkbox and the legend
    const cometEntry = document.getElementById("comet-entry-$uid");
    if (cometEntry) cometEntry.style.display = hasSingletons ? "" : "none";
    lastHasSingletons = hasSingletons;
    applyLegendVisibility();

    // Remove singletons unless comet checkbox is checked
    if (hasSingletons && !document.getElementById("comet-$uid")?.checked) {
        visibleNodes = new DataSet(nodes.get({filter: node => connectedIds.has(node.id)}));
    }

    // Empty-state notice (e.g. a time window with no collaboration at all).
    const emptyMsg = document.getElementById('empty-$uid');
    if (emptyMsg) emptyMsg.style.display = visibleNodes.length === 0 ? '' : 'none';

    // Gentle comet gravity: invisible springs pulling comets toward their
    // group's cluster (added to the rendered edges only, not the data model).
    const cometAttractors = buildCometAttractors(visibleNodes, visibleEdges, connectedIds);
    if (cometAttractors.length) visibleEdges.add(cometAttractors);

    // Set graph, nodes, and edges
    const network = new Network(container, {nodes: visibleNodes, edges: visibleEdges}, options);
    currentNetwork = network;
    network.once("afterDrawing", function () {
      network.fit({ maxZoomLevel: 3 });
    });
    const netNodes = network.body.data.nodes;
    const netEdges = network.body.data.edges;

    // Gradient edges
    network.on("beforeDrawing", function(ctx) {
        const selectedEdgeIds = network.getSelectedEdges();
        netEdges.forEach(edge => {
            const [fromColor, fromPos] = getNodeInfos(network, netNodes.get(edge.from))
            const [toColor, toPos] = getNodeInfos(network, netNodes.get(edge.to))

        if (fromColor && toColor && (fromColor !== toColor) && fromPos && toPos ) {
            let width = edge.width || 2;
            if (selectedEdgeIds.includes(edge.id) || hoveredEdgeId === edge.id
                || hoveredNodeId === edge.from || hoveredNodeId === edge.to) width *= 1.8;

            // Gradient
            const grad = ctx.createLinearGradient(fromPos.x, fromPos.y, toPos.x, toPos.y);
            grad.addColorStop(0, fromColor);
            grad.addColorStop(1, toColor);

            // Draw line
            ctx.save();
            ctx.strokeStyle = grad;
            ctx.lineWidth = width;
            ctx.beginPath();
            ctx.moveTo(fromPos.x, fromPos.y);
            ctx.lineTo(toPos.x, toPos.y);
            ctx.stroke();
            ctx.restore();
        }
    });
});

    // Hover tooltip & record
    network.on("hoverEdge", params => {
        const edge = netEdges.get(params.edge);
        network.body.container.title = edge.hover || '';
        hoveredEdgeId = params.edge;
    });

    network.on("blurEdge", params => {
        network.body.container.title = '';
        hoveredEdgeId = null;
    });

    network.on("hoverNode", params => {
        const node = netNodes.get(params.node);
        netNodes.update({id: node.id, borderWidth: 10})
        network.body.container.title = node.hover || '';
        hoveredNodeId = params.node;
    });
    network.on("blurNode", params => {
        const node = netNodes.get(params.node);
        netNodes.update({id: node.id, borderWidth: 5})
        network.body.container.title = '';
        hoveredNodeId = null;
    });


    // Modal overlay (rendered on demand from the shared publications dict)
    const modal = document.getElementById('modal-$uid');
    network.on("click", function(params) {
      if (params.nodes.length === 1) {
        const node = netNodes.get(params.nodes[0]);
        openModal(nodeTitleHtml(node), node.pub_keys || [], node.name);
      } else if (params.edges.length === 1) {
        const edge = netEdges.get(params.edges[0]);
        if (edge.attractor) { modal.style.display = "none"; return; }
        const a = netNodes.get(edge.from);
        const b = netNodes.get(edge.to);
        openModal(edgeTitleHtml(a, b), edge.pub_keys || [], a.name + '_' + b.name);
      } else {
        modal.style.display = "none";
      }
    });
}

// Pick the right parent for the modal: when our box is the fullscreen
// element, only its descendants are rendered, so the modal must live inside
// it. Outside fullscreen, we reparent to document.body to escape any
// transformed ancestor (JupyterLab cell wrappers) that would otherwise
// break position:fixed and click-outside-to-close.
function setModalParent() {
    const modal = document.getElementById('modal-$uid');
    if (!modal) return;
    const box = document.getElementById('box-$uid');
    const target = (document.fullscreenElement === box) ? box : document.body;
    if (modal.parentElement !== target) target.appendChild(modal);
}

// Event delegation on .modal-content: handles inline .bib / abstract toggles
// and the per-pre copy button (in modal-body), the "Show more…" expansion
// (in modal-body), and the per-list "Download .bib" action (now in
// modal-actions, so the body-only delegation that 0.5.4-pre-toolbar used
// would miss it). Plus the close X click and the background click.
function init_modal_handlers() {
    const modal = document.getElementById('modal-$uid');
    if (!modal) return;

    setModalParent();

    const modalContent = modal.querySelector('.modal-content');
    const modalClose = document.getElementById('modal-close-$uid');
    const modalBody = document.getElementById('modal-body-$uid');

    modalClose.addEventListener('click', () => { modal.style.display = "none"; });
    modalClose.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); modal.style.display = "none"; }
    });
    modal.addEventListener('click', event => {
        if (event.target === modal) modal.style.display = "none";
    });

    modalContent.addEventListener('click', function(event) {
        const t = event.target;

        // Inline toggles (.bib / abstract)
        if (t.matches('a.bib-toggle, a.abs-toggle')) {
            event.preventDefault();
            const cls = t.classList.contains('bib-toggle') ? 'pre.bib' : 'pre.abs';
            const pre = t.closest('.pub')?.querySelector(cls);
            if (pre) pre.hidden = !pre.hidden;
            return;
        }

        // sphinx_copybutton-style copy
        if (t.closest('.copybtn')) {
            event.preventDefault();
            const btn = t.closest('.copybtn');
            const pre = btn.parentElement;
            navigator.clipboard.writeText(bibText(pre)).then(() => {
                const orig = btn.textContent;
                btn.textContent = 'Copied!';
                btn.classList.add('copied');
                setTimeout(() => {
                    btn.textContent = orig;
                    btn.classList.remove('copied');
                }, 1500);
            });
            return;
        }

        // Show more
        if (t.matches('a.show-more')) {
            event.preventDefault();
            const list = t.closest('.pub-list');
            if (!list) return;
            list.querySelectorAll('.extra-publication').forEach(li => { li.style.display = 'list-item'; });
            t.parentElement.style.display = 'none';
            return;
        }

        // Download all publications in the modal as a .bib file. The button
        // lives in modal-actions but the <pre class="bib"> sit in modal-body.
        if (t.matches('a.dl-all-bib')) {
            event.preventDefault();
            const bibs = Array.from(modalBody.querySelectorAll('pre.bib')).map(bibText);
            if (bibs.length === 0) return;
            const blob = new Blob([bibs.join('\\n\\n') + '\\n'], {type: 'application/x-bibtex'});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = (t.dataset.name || 'publications') + '.bib';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(a.href);
            return;
        }
    });
}

// Decorate every <pre class="bib"> rendered into the modal with a copy button.
// Runs after each modal open via a MutationObserver on modal-body.
function init_copybuttons() {
    const modalBody = document.getElementById('modal-body-$uid');
    if (!modalBody) return;
    const decorate = () => {
        modalBody.querySelectorAll('pre.bib:not(.has-copybtn)').forEach(pre => {
            pre.classList.add('has-copybtn');
            const btn = document.createElement('button');
            btn.className = 'copybtn';
            btn.type = 'button';
            btn.title = 'Copy to clipboard';
            btn.textContent = 'Copy';
            pre.appendChild(btn);
        });
    };
    new MutationObserver(decorate).observe(modalBody, {childList: true, subtree: true});
    decorate();
}

// Wire the dual-handle year slider to the (shared) publications dict. Updating
// either handle sets `yearRange` and re-runs the single draw_graph() path, so
// node/edge/comet recomputation is reused verbatim. No slider is set up (and
// the menu entry is hidden) when no publication carries a year.
function setupTimeSlider() {
    const years = Object.values(publications).map(p => p.year).filter(y => y != null);
    const sMin = document.getElementById('slider-min-$uid');
    const sMax = document.getElementById('slider-max-$uid');
    const label = document.getElementById('slider-label-$uid');
    const menuEntry = document.querySelector('#menu-list-$uid [data-action="time-filter"]');
    if (!years.length || !sMin || !sMax) {
        if (menuEntry) menuEntry.closest('li').style.display = 'none';
        return;
    }
    const minY = Math.min(...years), maxY = Math.max(...years);
    for (const s of [sMin, sMax]) { s.min = minY; s.max = maxY; s.step = 1; }
    sMin.value = minY; sMax.value = maxY;
    function update() {
        // Take min/max of the two handles instead of forbidding them to cross:
        // a hard no-cross rule gets stuck when both sit on the same edge (you
        // can only grab the top handle, which then snaps back).
        const a = parseInt(sMin.value, 10), b = parseInt(sMax.value, 10);
        const lo = Math.min(a, b), hi = Math.max(a, b);
        yearRange = (lo === minY && hi === maxY) ? null : [lo, hi];
        if (label) label.textContent = yearRange ? (lo + ' – ' + hi) : ('All years (' + minY + ' – ' + maxY + ')');
        draw_graph();
    }
    sMin.addEventListener('input', update);
    sMax.addEventListener('input', update);
    update();
}

init_modal_handlers();
init_copybuttons();
setupTimeSlider();

draw_graph();

"""

# language=javascript
menu_script = """
function toggleFullscreen() {
    const elem = document.getElementById('box-$uid');
    if (!document.fullscreenElement) {
        const req = elem.requestFullscreen || elem.webkitRequestFullscreen || elem.msRequestFullscreen;
        if (req) req.call(elem);
    } else {
        const exit = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen;
        if (exit) exit.call(document);
    }
}

function downloadBlob(blob, filename) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
}

function downloadLabBib() {
    const bibs = Object.values(publications).map(p => p.bib).filter(Boolean);
    if (bibs.length === 0) return;
    const blob = new Blob([bibs.join('\\n\\n') + '\\n'], {type: 'application/x-bibtex'});
    downloadBlob(blob, safeFilename(labName) + '.bib');
}

// Native canvas rendering of the legend, bypassing html2canvas. Reason:
// html2canvas scans every stylesheet in the document (Jupyter / Sphinx
// load thousands of CSS rules) regardless of target size, costing ~10s
// on a real notebook even for our tiny legend. The legend structure is
// simple enough to draw directly: color box + checkbox + text per row.
function renderLegendToCanvas(legend, scale) {
    const lr = legend.getBoundingClientRect();
    const w = Math.max(1, Math.ceil(lr.width));
    const h = Math.max(1, Math.ceil(lr.height));
    const c = document.createElement('canvas');
    c.width = Math.ceil(w * scale);
    c.height = Math.ceil(h * scale);
    const ctx = c.getContext('2d');
    ctx.scale(scale, scale);

    const cs = getComputedStyle(legend);

    // Background + border (single radius, single border-color: matches the
    // current .legend rule).
    const radius = parseFloat(cs.borderTopLeftRadius) || 0;
    const bw = parseFloat(cs.borderTopWidth) || 0;
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(0, 0, w, h, radius);
    else ctx.rect(0, 0, w, h);
    ctx.fillStyle = cs.backgroundColor || '#ffffff';
    ctx.fill();
    if (bw > 0) {
        ctx.lineWidth = bw;
        ctx.strokeStyle = cs.borderTopColor || '#bbb';
        ctx.stroke();
    }

    ctx.font = cs.font || (cs.fontSize + ' ' + cs.fontFamily);
    ctx.textBaseline = 'middle';

    legend.querySelectorAll('.legend-entry, .comet-entry').forEach(entry => {
        if (entry.offsetParent === null) return;
        const er = entry.getBoundingClientRect();
        if (er.width === 0 || er.height === 0) return;

        // Color box (first <span> in the entry, with inline background-color).
        const colorBox = entry.querySelector('span');
        if (colorBox) {
            const sr = colorBox.getBoundingClientRect();
            const sc = getComputedStyle(colorBox);
            const bg = sc.backgroundColor;
            if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {
                ctx.fillStyle = bg;
                ctx.fillRect(sr.left - lr.left, sr.top - lr.top, sr.width, sr.height);
            }
        }

        // Checkbox (drawn manually: empty box + check mark if checked).
        const cb = entry.querySelector('input[type="checkbox"]');
        let textStartX = (er.left - lr.left) + 24;
        if (cb) {
            const cbr = cb.getBoundingClientRect();
            const cbx = cbr.left - lr.left;
            const cby = cbr.top - lr.top;
            ctx.strokeStyle = cs.color || '#888';
            ctx.lineWidth = 1;
            ctx.strokeRect(cbx + 0.5, cby + 0.5, Math.max(8, cbr.width - 1), Math.max(8, cbr.height - 1));
            if (cb.checked) {
                ctx.beginPath();
                ctx.moveTo(cbx + 3, cby + cbr.height / 2);
                ctx.lineTo(cbx + cbr.width * 0.4, cby + cbr.height - 4);
                ctx.lineTo(cbx + cbr.width - 3, cby + 3);
                ctx.lineWidth = 2;
                ctx.stroke();
            }
            textStartX = cbr.right - lr.left + 4;
        }

        // Text label: concat direct text-node children of the label element.
        let label = '';
        entry.childNodes.forEach(n => {
            if (n.nodeType === Node.TEXT_NODE) label += n.textContent;
        });
        label = label.trim();
        if (label) {
            ctx.fillStyle = cs.color || '#000000';
            ctx.fillText(label, textStartX, (er.top - lr.top) + er.height / 2);
        }
    });

    return c;
}

// Composite the vis-network canvas (already drawn, free to read) with the
// natively-rendered legend. No CDN, no DOM walk, sub-millisecond on top of
// the network read.
function captureBox() {
    const networkCanvas = currentNetwork && currentNetwork.canvas && currentNetwork.canvas.frame
        ? currentNetwork.canvas.frame.canvas
        : null;
    if (!networkCanvas) throw new Error('Network canvas unavailable');

    const out = document.createElement('canvas');
    out.width = networkCanvas.width;
    out.height = networkCanvas.height;
    const ctx = out.getContext('2d');
    ctx.drawImage(networkCanvas, 0, 0);

    const legend = document.getElementById('legend-$uid');
    if (legend && legend.style.display !== 'none' && legend.offsetParent !== null) {
        try {
            const visEl = document.getElementById('vis-$uid');
            const visRect = visEl.getBoundingClientRect();
            const legendRect = legend.getBoundingClientRect();
            const scale = networkCanvas.width / visRect.width;
            const legendCanvas = renderLegendToCanvas(legend, scale);
            const dx = (legendRect.left - visRect.left) * scale;
            const dy = (legendRect.top - visRect.top) * scale;
            ctx.drawImage(legendCanvas, dx, dy);
        } catch (err) {
            console.warn('Legend overlay failed:', err);
        }
    }
    return out;
}

function downloadPng() {
    try {
        const canvas = captureBox();
        canvas.toBlob(blob => {
            if (blob) downloadBlob(blob, safeFilename(labName) + '.png');
        }, 'image/png');
    } catch (err) {
        console.warn('PNG export failed:', err);
    }
}

function copyPngToClipboard() {
    if (!navigator.clipboard || typeof window.ClipboardItem !== 'function') {
        console.warn('Clipboard image API unavailable in this browser/context.');
        return;
    }
    try {
        const canvas = captureBox();
        canvas.toBlob(blob => {
            if (!blob) return;
            navigator.clipboard.write([new ClipboardItem({'image/png': blob})])
                .catch(err => console.warn('PNG clipboard copy failed:', err));
        }, 'image/png');
    } catch (err) {
        console.warn('PNG clipboard copy failed:', err);
    }
}

function applyLegendVisibility() {
    const legend = document.getElementById("legend-$uid");
    if (!legend) return;
    const auto = (Object.keys(options.groups).length > 1 || lastHasSingletons);
    const visible = legendVisibilityOverride !== null ? legendVisibilityOverride : auto;
    legend.style.display = visible ? "" : "none";
    const label = document.querySelector('#menu-list-$uid [data-action="toggle-legend"] .menu-label');
    if (label) label.textContent = visible ? 'Hide Legend' : 'Show Legend';
}

function toggleLegend() {
    const legend = document.getElementById("legend-$uid");
    if (!legend) return;
    const currentlyVisible = legend.style.display !== 'none';
    legendVisibilityOverride = !currentlyVisible;
    applyLegendVisibility();
}

// Legend labels toggle. Each entry ships a primary label (data-default, the
// initially visible text) and an alternative one (data-alt). We swap the
// visible text node — kept a *direct* child of the entry so the PNG export
// reads the current wording — and expose the other version via the title
// (hover), per the user request "le hover donne de toute façon l'autre version".
let legendMode = 'default'; // 'default' | 'alt'
function applyLegendMode() {
    const legend = document.getElementById('legend-$uid');
    if (legend) {
        const showAlt = legendMode === 'alt';
        legend.querySelectorAll('.legend-entry').forEach(entry => {
            const def = entry.getAttribute('data-default');
            const alt = entry.getAttribute('data-alt');
            if (def === null || alt === null) return;
            let textNode = null;
            entry.childNodes.forEach(n => {
                if (n.nodeType === Node.TEXT_NODE && n.textContent.trim()) textNode = n;
            });
            if (textNode) textNode.textContent = showAlt ? alt : def;
            entry.setAttribute('title', showAlt ? def : alt);
        });
    }
    const label = document.querySelector('#menu-list-$uid [data-action="legend-mode"] .menu-label');
    if (label) label.textContent = legendMode === 'alt' ? 'Use default labels' : 'Use alternative labels';
}
function toggleLegendMode() {
    legendMode = (legendMode === 'alt') ? 'default' : 'alt';
    applyLegendMode();
}

function toggleTimeFilter() {
    const slider = document.getElementById('slider-$uid');
    if (!slider) return;
    const visible = slider.style.display !== 'none';
    slider.style.display = visible ? 'none' : 'block';
    const label = document.querySelector('#menu-list-$uid [data-action="time-filter"] .menu-label');
    if (label) label.textContent = visible ? 'Time filter' : 'Hide time filter';
}

// Theme override. 'auto' follows the host (Jupyter / Sphinx) via CSS var
// chains; 'light'/'dark' force a palette by adding a class that redefines those
// vars. The class is applied to both the box and the modal (the modal is
// reparented to <body> outside fullscreen, so it must carry the class itself).
let themeMode = $theme; // 'auto' | 'light' | 'dark'
function applyTheme() {
    for (const id of ['box-$uid', 'modal-$uid']) {
        const el = document.getElementById(id);
        if (!el) continue;
        el.classList.remove('gm-light', 'gm-dark');
        if (themeMode === 'light') el.classList.add('gm-light');
        else if (themeMode === 'dark') el.classList.add('gm-dark');
    }
    const label = document.querySelector('#menu-list-$uid [data-action="theme"] .menu-label');
    if (label) label.textContent = 'Theme: ' + themeMode;
}
function cycleTheme() {
    themeMode = themeMode === 'auto' ? 'light' : themeMode === 'light' ? 'dark' : 'auto';
    applyTheme();
}

function refreshFullscreenLabels() {
    const inFs = !!document.fullscreenElement;
    const label = inFs ? 'Exit Full Screen' : 'Full Screen';
    const btn = document.getElementById('fullscreen-$uid');
    if (btn) {
        btn.title = label;
        btn.setAttribute('aria-label', label);
    }
    const menuLabel = document.querySelector('#menu-list-$uid [data-action="fullscreen"] .menu-label');
    if (menuLabel) menuLabel.textContent = label;
}

const menuActions = {
    'redraw': draw_graph,
    'fullscreen': toggleFullscreen,
    'toggle-legend': toggleLegend,
    'legend-mode': toggleLegendMode,
    'time-filter': toggleTimeFilter,
    'theme': cycleTheme,
    'dl-bib': downloadLabBib,
    'dl-png': downloadPng,
    'copy-png': copyPngToClipboard,
};

const menuBtn = document.getElementById('menu-$uid');
const menuList = document.getElementById('menu-list-$uid');
const menuWrap = document.getElementById('menu-wrap-$uid');

function setMenuOpen(open) {
    menuList.hidden = !open;
    menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
}

menuBtn.addEventListener('click', function(event) {
    event.preventDefault();
    event.stopPropagation();
    setMenuOpen(menuList.hidden);
});

menuList.addEventListener('click', function(event) {
    const item = event.target.closest('a.menu-item');
    if (!item) return;
    event.preventDefault();
    setMenuOpen(false);
    const action = menuActions[item.dataset.action];
    if (action) action();
});

document.addEventListener('click', function(event) {
    if (!menuList.hidden && !menuWrap.contains(event.target)) {
        setMenuOpen(false);
    }
});

document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape' && !menuList.hidden) {
        setMenuOpen(false);
    }
});

document.getElementById('fullscreen-$uid').addEventListener('click', function(event) {
    event.preventDefault();
    toggleFullscreen();
});

document.addEventListener('fullscreenchange', () => {
    refreshFullscreenLabels();
    setModalParent();
});
refreshFullscreenLabels();
applyTheme();

// Reflect the actual filename in the menu entry, e.g. "Download Céline_Comte.bib".
const dlBibLabel = document.querySelector('#menu-list-$uid [data-action="dl-bib"] .menu-label');
if (dlBibLabel) dlBibLabel.textContent = 'Download ' + safeFilename(labName) + '.bib';

"""

# language=javascript
legend_script = """
// Refresh when boxes are changed
document.querySelectorAll("#legend-$uid input").forEach(cb => {
  cb.addEventListener('change', draw_graph);
});


"""


default_script = Template(draw_script + menu_script + legend_script)
