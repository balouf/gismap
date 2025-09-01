from string import Template
import uuid
import json


vis_template = Template("""
<div class="gismap-content">
<div id="${container_id}"></div>
<a
  href="https://balouf.github.io/gismap/"
  target="_blank"
  id="gismap-brand"
  style="position: absolute; left: 10px; bottom: 10px; text-decoration: none; color: #888; font-size: min(2vw, 10px);
  z-index: 10; pointer-events: auto;"
>
  &copy; Gismap 2025
</a>
<div id="${modal_id}" class="modal">
<div class="modal-content">
    <span class="close" id="${modal_close_id}">&times;</span>
    <div id="${modal_body_id}"></div>
  </div>
</div>
</div>
<style>
.gismap-content {
position: relative;
width: 100%;
height: 80vh !important;
max-width: 100vw;
max-height: 100vh !important;
}
  /* Styles adaptatifs pour dark/light */
/* Default: dark mode styles */
#${container_id} {
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  border: 1px solid #444;
  background: #181818;
}

.modal {
  display: none;
  position: fixed;
  z-index: 1000;
  left: 0; top: 0;
  width: 100%; height: 100%;
  overflow: auto;
  background-color: rgba(10,10,10,0.85);
}

.modal-content {
  background-color: #23272e;
  color: #f0f0f0;
  margin: 10% auto;
  padding: 24px;
  border: 1px solid #888;
  width: 50%;
  border-radius: 8px;
  box-shadow: 0 5px 15px rgba(0,0,0,.6);
}

.close {
  color: #aaa;
  float: right;
  font-size: 28px;
  font-weight: bold;
  cursor: pointer;
}

.close:hover, .close:focus {
  color: #fff;
  text-decoration: none;
  cursor: pointer;
}

/* PyData Sphinx Light Theme */
html[data-theme="light"] #${container_id},
body[data-jp-theme-light="true"] #${container_id} {
  background: #fff;
  border: 1px solid #ccc;
}

html[data-theme="light"] .modal,
body[data-jp-theme-light="true"] .modal {
  background-color: rgba(220,220,220,0.85);
}

html[data-theme="light"] .modal-content,
body[data-jp-theme-light="true"] .modal-content {
  background: #fff;
  color: #222;
  border: 1px solid #888;
}

html[data-theme="light"] .close,
body[data-jp-theme-light="true"] .close {
  color: #222;
}

html[data-theme="light"] .close:hover, html[data-theme="light"] .close:focus,
body[data-jp-theme-light="true"] .close:hover, body[data-jp-theme-light="true"] .close:focus {
  color: #555;
}

/* Fallback: system light mode */
@media (prefers-color-scheme: light) {
  #${container_id} {
    background: #fff;
    border: 1px solid #ccc;
  }
  .modal {
    background-color: rgba(220,220,220,0.85);
  }
  .modal-content {
    background: #fff;
    color: #222;
    border: 1px solid #888;
  }
  .close {
    color: #222;
  }
  .close:hover, .close:focus {
    color: #555;
  }
}
</style>
<script type="text/javascript">
(function() {
  // Détection du thème
function getTheme() {
  // Try PyData Sphinx theme on <html>
  const pydataTheme = document.documentElement.getAttribute("data-theme");
  if (pydataTheme === "dark" || pydataTheme === "light") {
    return pydataTheme;
  }

  // Try JupyterLab theme on <body>
  const jupyterLabTheme = document.body.getAttribute("data-jp-theme-name");
  if (jupyterLabTheme) {
    // Simplify theme name to 'dark' or 'light'
    const lowerName = jupyterLabTheme.toLowerCase();
    if (lowerName.includes("dark")) {
      return "dark";
    }
    if (lowerName.includes("light")) {
      return "light";
    }
  }

  // Fallback to system preference
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? "dark" : "light";
};
  function getVisOptions(theme) {
    if (theme === 'dark') {
      return {
        nodes: {
          shape: 'circle', size: 20,
          font: { size: 16, color: '#f0f0f0' },
          color: {
            background: '#222e3c',
            border: '#5d90f5',
            highlight: { background: '#2f3d4d', border: '#f5a25d' }
          },
          borderWidth: 2
        },
        edges: {
          width: 2,
          color: { color: '#888', highlight: '#f5a25d' },
          smooth: { type: 'continuous' }
        },
        interaction: { hover: true }
      };
    } else {
      return {
        nodes: {
          shape: 'circle', size: 20,
          font: { size: 16, color: '#222' },
          color: {
            background: '#e3eaff',
            border: '#3d6cf7',
            highlight: { background: '#fffbe6', border: '#f5a25d' }
          },
          borderWidth: 2
        },
        edges: {
          width: 2,
          color: { color: '#848484', highlight: '#f5a25d' },
          smooth: { type: 'continuous' }
        },
        interaction: { hover: true }
      };
    }
  };

  var physics = {
  physics: {
    solver: "forceAtlas2Based",
    forceAtlas2Based: {
      gravitationalConstant: -50,
      centralGravity: 0.01,
      springLength: 200,
      springConstant: 0.08,
      damping: 0.98,
      avoidOverlap: 1
    },
    maxVelocity: 10,
    minVelocity: 0.9,
    stabilization: {
      enabled: true,
      iterations: 2000,
      updateInterval: 50,
      onlyDynamicEdges: false,
      fit: true
    },
    timestep: 0.25
  }
};

  function renderNetwork() {
  const nodes = new vis.DataSet(${nodes_json});
  const edges = new vis.DataSet(${edges_json});
  const container = document.getElementById('${container_id}');
  let network = null;
    const theme = getTheme();
    const options = getVisOptions(theme);
    network = new vis.Network(container, { nodes: nodes, edges: edges }, options);
    network.setOptions(physics)
    // Tooltip survol
    network.on("hoverNode", function(params) {
      const node = nodes.get(params.node);
      network.body.container.title = node.hover || '';
    });
    network.on("blurNode", function(params) {
      network.body.container.title = '';
    });
    network.on("hoverEdge", function(params) {
      const edge = edges.get(params.edge);
      network.body.container.title = edge.hover || '';
    });
    network.on("blurEdge", function(params) {
      network.body.container.title = '';
    });
    // Modal overlay
    const modal = document.getElementById('${modal_id}');
    const modalBody = document.getElementById('${modal_body_id}');
    const modalClose = document.getElementById('${modal_close_id}');
    network.on("click", function(params) {
      if (params.nodes.length === 1) {
        const node = nodes.get(params.nodes[0]);
        modalBody.innerHTML = node.overlay || '';
        modal.style.display = "block";
      } else if (params.edges.length === 1) {
        const edge = edges.get(params.edges[0]);
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
  };

  function loadVisAndRender() {
  if (typeof vis === 'undefined') {
    var script = document.createElement('script');
    script.src = "https://unpkg.com/vis-network/standalone/umd/vis-network.min.js";
    script.type = "text/javascript";
    script.onload = function() {
      console.log("vis-network loaded dynamically");
      renderNetwork();  // Graph init after vis is loaded
    };
    document.head.appendChild(script);
  } else {
    console.log("vis-network already loaded");
    renderNetwork();  // Graph init immediately
  }
}
loadVisAndRender();

  // Adapter dynamiquement si le thème change
  window.addEventListener("theme-changed", () => loadVisAndRender());
  const observer = new MutationObserver(mutations => {
  for (const mutation of mutations) {
    if (mutation.type === "attributes" && mutation.attributeName === "data-jp-theme-name") {
      loadVisAndRender();
    }
  }
    });
    observer.observe(document.body, { attributes: true });
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => loadVisAndRender());
    };
})();
</script>
""")


def generate_html(nodes, edges):
    """
    Parameters
    ----------
    nodes: :class:`list`
    edges: :class:`list`

    Returns
    -------
    :class:`str`
    """
    uid = str(uuid.uuid4())[:8]  # identifiant unique pour éviter les collisions
    container_id = f"mynetwork_{uid}"
    modal_id = f"modal_{uid}"
    modal_body_id = f"modal_body_{uid}"
    modal_close_id = f"modal_close_{uid}"
    nodes_json = json.dumps(nodes)
    edges_json = json.dumps(edges)
    dico = {
        "container_id": container_id,
        "modal_id": modal_id,
        "modal_body_id": modal_body_id,
        "modal_close_id": modal_close_id,
        "nodes_json": nodes_json,
        "edges_json": edges_json,
    }
    return vis_template.substitute(dico)  # html_template
