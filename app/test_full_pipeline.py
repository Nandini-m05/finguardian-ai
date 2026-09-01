import sys
import asyncio
import uuid

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from datetime import datetime, timezone
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.config import settings
from app.graph import build_graph


async def main():
    async with AsyncPostgresSaver.from_conn_string(settings.langgraph_db_url) as checkpointer:
        await checkpointer.setup()
        graph = build_graph(checkpointer)

        thread_id = f"test-full-pipeline-{uuid.uuid4().hex[:8]}"
        print(f"Using thread_id: {thread_id}\n")
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "request_id": f"test-{uuid.uuid4().hex[:8]}",
            "symbol": "AAPL",
            "asset_type": "stock",
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }

        result = await graph.ainvoke(initial_state, config)
        print("Risk score:", result["risk_score"])
        print("Fraud flag:", result["fraud_flag"])
        print("Requires human review:", result["requires_human_review"])
        print("Human decision:", result.get("human_decision"))
        print("Recommendation:", result["recommendation"])
        print("Rationale:", result["decision_rationale"])
        print("\nFinal report:\n")
        print(result["final_report"])
        print("\nAlerts sent:", result.get("alerts_sent"))
        print("\nFull agent log:")
        for entry in result["agent_log"]:
            print(" -", entry)


if __name__ == "__main__":
    asyncio.run(main())