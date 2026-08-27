import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.config import settings

class State(TypedDict):
    messages: list

def greet_node(state: State) -> dict:
    return {"messages": state["messages"] + ["Hello from your first LangGraph node!"]}

async def main():
    builder = StateGraph(State)
    builder.add_node("greet", greet_node)
    builder.add_edge(START, "greet")
    builder.add_edge("greet", END)

    async with AsyncPostgresSaver.from_conn_string(settings.langgraph_db_url) as checkpointer:
        await checkpointer.setup()
        graph = builder.compile(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": "test-thread-1"}}
        result = await graph.ainvoke({"messages": []}, config)
        print("Result:", result)

        state = await graph.aget_state(config)
        print("Checkpointed state:", state.values)

if __name__ == "__main__":
    asyncio.run(main())