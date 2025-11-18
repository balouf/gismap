from string import Template


# language=javascript
draw_script = """
import { DataSet, Network } from $vis_url;

const nodes = new DataSet($nodes);
const edges = new DataSet($edges);
const options = $options;
const container = document.getElementById('vis-$uid');
let hoveredEdgeId = null;
let hoveredNodeId = null;

// Get the group color and position of a node. Useful for gradient edges
function getNodeInfos(network, node) {
    if (node && !options.groups?.[node.group]?.hidden) {
        return [options.groups[node.group].color, network.getPositions([node.id])[node.id]]
    }
    return [false, false];
}


// main course
function draw_graph() {
    // No clean redraw so far, so we re-create everything :(
    // const show_comets = document.getElementById("comet-$uid").checked;
    document.querySelectorAll('#legend-$uid .legend-checkbox').forEach(cb => {
    const group = cb.getAttribute('data-group');
    options.groups[group].hidden = !cb.checked;
        });

    //nodes.forEach(node => nodes.update({id: node.id, hidden: !show_comets && !node.connected}));

    // First compute the nodes to display.
    var visibleNodes = new DataSet(nodes.get({
      filter: node => !options.groups?.[node.group]?.hidden}));
    var visibleNodeIds = new Set(visibleNodes.map(node => node.id));
    const visibleEdges = new DataSet(edges.get({
        filter: edge => visibleNodeIds.has(edge.from) && visibleNodeIds.has(edge.to)}));
    if (!document.getElementById("comet-$uid")?.checked) {
        visibleNodeIds = new Set();
        visibleEdges.forEach(edge => {
            visibleNodeIds.add(edge.from);
            visibleNodeIds.add(edge.to);
        });
        visibleNodes = new DataSet(nodes.get({filter: node => visibleNodeIds.has(node.id)}));
    }



    const network = new Network(container, {nodes: visibleNodes, edges: visibleEdges}, options);
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
            if (selectedEdgeIds.includes(edge.id) || hoveredEdgeId === edge.id || hoveredNodeId === edge.from || hoveredNodeId === edge.to) width *= 1.8;

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


    // Modal overlay
    const modal = document.getElementById('modal-$uid');
    const modalBody = document.getElementById('modal-body-$uid');
    const modalClose = document.getElementById('modal-close-$uid');
    network.on("click", function(params) {
      if (params.nodes.length === 1) {
        const node = netNodes.get(params.nodes[0]);
        modalBody.innerHTML = node.overlay || '';
        modal.style.display = "block";
      } else if (params.edges.length === 1) {
        const edge = netEdges.get(params.edges[0]);
        modalBody.innerHTML = edge.overlay || '';
        modal.style.display = "block";
      } else {
        modal.style.display = "none";
      }
    });
    modalClose.onclick = function() { modal.style.display = "none"; };
    window.onclick = function(event) {
      if (event.target == modal) { modal.style.display = "none"; }
    };
}

draw_graph();

"""

# language=javascript
redraw_script = """
document.getElementById('redraw-$uid').addEventListener('click', function(event) {
    event.preventDefault();  // Prevent page jump
    draw_graph();
});

"""

# language=javascript
fs_script = """
document.getElementById('fullscreen-$uid').addEventListener('click', function(event) {
    event.preventDefault();
    let elem = document.getElementById('box-$uid');
    if (!document.fullscreenElement) {
        // Request fullscreen mode
        if (elem.requestFullscreen) {
            elem.requestFullscreen();
        } else if (elem.webkitRequestFullscreen) { /* Safari */
            elem.webkitRequestFullscreen();
        } else if (elem.msRequestFullscreen) { /* IE11 */
            elem.msRequestFullscreen();
        }
    } else {
        // Exit fullscreen mode
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) { /* Safari */
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) { /* IE11 */
            document.msExitFullscreen();
        }
    }
});

"""

# language=javascript
legend_script = """
function updateGroupsVisibility() {
  document.querySelectorAll('#legend-$uid .legend-checkbox').forEach(cb => {
    const group = cb.getAttribute('data-group');
    options.groups[group].hidden = !cb.checked;
  });
  draw_graph();
}

// Ajout de l’event à chaque checkbox
// document.querySelectorAll('#legend-$uid .legend-checkbox').forEach(cb => {
//  cb.addEventListener('change', updateGroupsVisibility);
//});

// Ajout de l’event à chaque checkbox
document.querySelectorAll("#legend-$uid input").forEach(cb => {
  cb.addEventListener('change', draw_graph);
});


"""


default_script = Template(draw_script+redraw_script+fs_script+legend_script)
