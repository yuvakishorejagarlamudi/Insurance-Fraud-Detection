import networkx as nx

def build_graph(edges: list[dict]) -> nx.Graph:
    graph = nx.Graph()
    for edge in edges:
        graph.add_edge(
            f"{edge['source_type']}:{edge['source_id']}",
            f"{edge['target_type']}:{edge['target_id']}",
            relationship=edge.get("relationship_type", "RELATED"),
            strength=float(edge.get("strength", 1.0)),
        )
    return graph

def summarize_graph(graph: nx.Graph) -> dict:
    components = sorted((list(c) for c in nx.connected_components(graph)), key=len, reverse=True)
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "components": len(components),
        "largest_component_size": len(components[0]) if components else 0,
        "degree": dict(graph.degree()),
    }
