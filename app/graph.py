from langgraph.graph import StateGraph, START, END
from app.agents.state import AgentState
from app.agents.data_collector import data_collector_node
from app.agents.market_analysis import market_analysis_node
from app.agents.news_intelligence import news_intelligence_node
from app.agents.risk_assessment import risk_assessment_node
from app.agents.fraud_features import fraud_detection_node
from app.agents.human_review import human_review_node
from app.agents.recommendation import recommendation_node
from app.agents.report import report_node
from app.agents.alert_notification import alert_notification_node


def build_graph(checkpointer):
    """Build and compile the full FinGuardian agent graph.

    Single source of truth for graph wiring - both the real FastAPI app
    and test scripts import this, so they can never silently drift apart
    the way two hand-copied versions did.
    """
    builder = StateGraph(AgentState)
    builder.add_node("data_collector", data_collector_node)
    builder.add_node("market_analysis", market_analysis_node)
    builder.add_node("news_intelligence", news_intelligence_node)
    builder.add_node("risk_assessment", risk_assessment_node)
    builder.add_node("fraud_detection", fraud_detection_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("recommendation", recommendation_node)
    builder.add_node("report", report_node)
    builder.add_node("alert_notification", alert_notification_node)
    builder.add_edge(START, "data_collector")
    builder.add_edge("data_collector", "market_analysis")
    builder.add_edge("market_analysis", "news_intelligence")
    builder.add_edge("news_intelligence", "risk_assessment")
    builder.add_edge("risk_assessment", "fraud_detection")
    builder.add_edge("fraud_detection", "human_review")
    builder.add_edge("human_review", "recommendation")
    builder.add_edge("recommendation", "report")
    builder.add_edge("report", "alert_notification")
    builder.add_edge("alert_notification", END)
    return builder.compile(checkpointer=checkpointer)
 