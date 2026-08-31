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
from app.agents.fraud_features import score_fraud


async def main():
    builder = StateGraph(AgentState)
    builder.add_node("data_collector", data_collector_node)
    builder.add_node("market_analysis", market_analysis_node)
    builder.add_node("news_intelligence", news_intelligence_node)
    builder.add_edge(START, "data_collector")
    builder.add_edge("data_collector", "market_analysis")
    builder.add_edge("market_analysis", "news_intelligence")
    builder.add_edge("news_intelligence", END)

    async with AsyncPostgresSaver.from_conn_string(settings.langgraph_db_url) as checkpointer:
        await checkpointer.setup()
        graph = builder.compile(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": "test-fraud-features-1"}}
        initial_state = {
            "request_id": "test-005",
            "symbol": "AAPL",
            "asset_type": "stock",
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }

        result = await graph.ainvoke(initial_state, config)

    fraud_result = score_fraud(result)
    print("Fraud flag:", fraud_result["fraud_flag"])
    print("Fraud confidence (XGBoost):", fraud_result["fraud_confidence"])
    print("Isolation Forest flag:", fraud_result["isolation_forest_flag"])
    print("\nFeatures used:", fraud_result["features_used"])
    print("\nSHAP explanation:")
    for name, value in fraud_result["shap_explanation"].items():
        print(f"  {name}: {value:+.3f}")


if __name__ == "__main__":
    asyncio.run(main())