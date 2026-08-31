import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command
from app.config import settings
from app.agents.state import AgentState
from app.agents.human_review import human_review_node


async def main():
    builder = StateGraph(AgentState)
    builder.add_node("human_review", human_review_node)
    builder.add_edge(START, "human_review")
    builder.add_edge("human_review", END)

    async with AsyncPostgresSaver.from_conn_string(settings.langgraph_db_url) as checkpointer:
        await checkpointer.setup()
        graph = builder.compile(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": "test-human-review-1"}}
        # Manually simulating a flagged case - no real pipeline run needed
        initial_state = {
            "request_id": "test-007",
            "symbol": "AAPL",
            "asset_type": "stock",
            "requested_at": "2026-08-31T00:00:00Z",
            "requires_human_review": True,
            "risk_score": 82.0,
            "fraud_confidence": 0.71,
            "risk_factors": ["Elevated price volatility (7.2)", "Large single-day price move (+18.4%)"],
            "shap_explanation": {"volatility": 3.1, "price_change_pct": 2.4},
        }

        # This call should PAUSE, not run to completion
        result = await graph.ainvoke(initial_state, config)
        print("First call result:", result)

        state = await graph.aget_state(config)
        print("\nGraph paused. Next node(s):", state.next)
        print("Raw task/interrupt info:", state.tasks)

        # Simulate an analyst approving the flagged case, resuming the same thread
        print("\n--- Simulating analyst decision: approve ---")
        final_result = await graph.ainvoke(Command(resume="approved"), config)
        print("Final result:", final_result)


if __name__ == "__main__":
    asyncio.run(main())