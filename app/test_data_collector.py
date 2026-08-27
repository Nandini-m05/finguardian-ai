import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from datetime import datetime, timezone
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.config import settings
from app.agents.state import AgentState
from app.agents.data_collector import data_collector_node, DATA_COLLECTOR_STREAM
from app.events.redis_client import get_redis_client


async def main():
    builder = StateGraph(AgentState)
    builder.add_node("data_collector", data_collector_node)
    builder.add_edge(START, "data_collector")
    builder.add_edge("data_collector", END)

    async with AsyncPostgresSaver.from_conn_string(settings.langgraph_db_url) as checkpointer:
        await checkpointer.setup()
        graph = builder.compile(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": "test-data-collector-3"}}
        initial_state = {
            "request_id": "test-001",
            "symbol": "AAPL",
            "asset_type": "stock",
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }

        result = await graph.ainvoke(initial_state, config)
        print("Result:", result)

    # Verify the event actually landed on the Redis Stream
    redis_client = get_redis_client()
    entries = await redis_client.xrange(DATA_COLLECTOR_STREAM, count=5)
    print("\nLatest entries on stream:", DATA_COLLECTOR_STREAM)
    for entry_id, fields in entries:
        print(f"  {entry_id}: {fields}")
    await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())