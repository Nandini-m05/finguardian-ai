import sys
import asyncio
import uuid

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.config import settings
from app.graph import build_graph


async def main():
    async with AsyncPostgresSaver.from_conn_string(settings.langgraph_db_url) as checkpointer:
        await checkpointer.setup()
        graph = build_graph(checkpointer)

        thread_id = f"demo-flagged-{uuid.uuid4().hex[:6]}"
        config = {"configurable": {"thread_id": thread_id}}

        # Write a checkpoint as if fraud_detection just finished - skips
        # data_collector/market_analysis/news_intelligence entirely, so
        # this costs zero Alpha Vantage calls.
        await graph.aupdate_state(
            config,
            {
                "request_id": "demo-001",
                "symbol": "XYZ",
                "asset_type": "stock",
                "requested_at": "2026-09-01T00:00:00Z",
                "risk_score": 82.0,
                "risk_factors": ["Elevated price volatility (7.2)", "Large single-day price move (+18.4%)"],
                "fraud_flag": True,
                "fraud_confidence": 0.71,
                "shap_explanation": {"volatility": 3.1, "price_change_pct": 2.4},
                "requires_human_review": True,
            },
            as_node="fraud_detection",
        )

        result = await graph.ainvoke(None, config)
        print("Paused result:", result)
        print("\n>>> thread_id to resume via /analyze/{thread_id}/resume:", thread_id)


if __name__ == "__main__":
    asyncio.run(main())