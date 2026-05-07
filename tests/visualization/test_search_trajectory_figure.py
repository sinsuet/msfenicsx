from pathlib import Path


def test_search_trajectory_figures_write_png_and_pdf(tmp_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")

    from visualization.figures.search_trajectory_network import (
        render_search_trajectory_network,
        render_search_trajectory_nodes_by_vector,
    )

    nodes = [
        {
            "node_id": "n1",
            "visit_count": 2,
            "vector_count": 1,
            "vectors": "V1",
            "first_generation": 0,
            "last_generation": 0,
            "pareto_member": False,
        },
        {
            "node_id": "n2",
            "visit_count": 4,
            "vector_count": 2,
            "vectors": "V1|V2",
            "first_generation": 1,
            "last_generation": 1,
            "pareto_member": True,
        },
    ]
    edges = [
        {"source": "n1", "target": "n2", "vector_id": "V1", "weight": 3},
    ]
    metrics = [
        {"scope": "vector", "vector_id": "V1", "num_nodes": 2},
        {"scope": "vector", "vector_id": "V2", "num_nodes": 1},
    ]

    network_output = tmp_path / "search_trajectory_network.png"
    bar_output = tmp_path / "search_trajectory_nodes_by_vector.png"

    render_search_trajectory_network(nodes=nodes, edges=edges, output=network_output)
    render_search_trajectory_nodes_by_vector(metrics=metrics, output=bar_output)

    assert network_output.exists()
    assert network_output.with_name("pdf").joinpath("search_trajectory_network.pdf").exists()
    assert bar_output.exists()
    assert bar_output.with_name("pdf").joinpath("search_trajectory_nodes_by_vector.pdf").exists()
