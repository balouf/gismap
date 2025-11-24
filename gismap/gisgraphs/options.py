physics = {
    "solver": "forceAtlas2Based",
    "forceAtlas2Based": {
        "gravitationalConstant": -50,
        "centralGravity": 0.01,
        "springLength": 200,
        "springConstant": 0.08,
        "damping": 0.98,
        "avoidOverlap": 1,
    },
    "maxVelocity": 10,
    "minVelocity": 0.9,
    "stabilization": {
        "enabled": True,
        "iterations": 500,
        "updateInterval": 50,
        "onlyDynamicEdges": False,
        "fit": True,
    },
    "timestep": 0.25,
}

nodes = {
    "shape": "circle",
    "size": 20,
    "font": {"size": 16, "color": "#111"},
    "color": "rgb(59, 101, 178)",
    "borderWidth": 5,
}

edges = {
    "width": 2,
    # 'color': {'color': '#888', 'highlight': '#f5a25d'},
    "smooth": False,  # {"type": 'continuous'}
}

interaction = {"hover": True}
