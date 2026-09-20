from app.graph import build_graph

EXPECTED_NODES = {
    "__start__", "data_collector", "market_analysis", "news_intelligence",
    "risk_assessment", "fraud_detection", "human_review", "recommendation",
    "report", "alert_notification", "__end__",
}


def test_graph_compiles_with_all_nodes():
    graph = build_graph(checkpointer=None)
    nodes = set(graph.get_graph().nodes.keys())
    assert nodes == EXPECTED_NODES
