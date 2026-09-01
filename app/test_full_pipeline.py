import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from datetime import datetime, timezone
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.config import settings
from app.agents.state import AgentState
from app.agents.data_collector import data_collector_node
from app.agents.market_analysis import market_analysis_node
from app.agents.news_intelligence import news_intelligence_node
from app.agents.risk_assessment import risk_assessment_node
from app.agents.fraud_features import fraud_detection_node
from app.agents.human_review import human_review_node


async def main():
    builder = StateGraph(AgentState)
    builder.add_node("data_collector", data_collector_node)
    builder.add_node("market_analysis", market_analysis_node)
    builder.add_node("news_intelligence", news_intelligence_node)
    builder.add_node("risk_assessment", risk_assessment_node)
    builder.add_node("fraud_detection", fraud_detection_node)
    builder.add_node("human_review", human_review_node)
    builder.add_edge(START, "data_collector")
    builder.add_edge("data_collector", "market_analysis")
    builder.add_edge("market_analysis", "news_intelligence")
    builder.add_edge("news_intelligence", "risk_assessment")
    builder.add_edge("risk_assessment", "fraud_detection")
    builder.add_edge("fraud_detection", "human_review")
    builder.add_edge("human_review", END)

    async with AsyncPostgresSaver.from_conn_string(settings.langgraph_db_url) as checkpointer:
        await checkpointer.setup()
        graph = builder.compile(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": "test-full-pipeline-1"}}
        initial_state = {
            "request_id": "test-008",
            "symbol": "AAPL",
            "asset_type": "stock",
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }

        result = await graph.ainvoke(initial_state, config)
        print("Risk score:", result["risk_score"])
        print("Fraud flag:", result["fraud_flag"])
        print("Requires human review:", result["requires_human_review"])
        print("Human decision:", result.get("human_decision"))
        print("\nFull agent log:")
        for entry in result["agent_log"]:
            print(" -", entry)


if __name__ == "__main__":
    asyncio.run(main())