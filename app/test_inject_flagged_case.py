import sys
import asyncio
import uuid

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy import select
from app.config import settings
from app.graph import build_graph
from app.database import async_session
from app.models import Analysis, User


async def main():
    email = input("Email of the account to attach this test case to: ").strip()

    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            print(f"No user found with email {email}")
            return

    thread_id = f"demo-flagged-{uuid.uuid4().hex[:6]}"
    risk_factors = ["Elevated price volatility (7.2)", "Large single-day price move (+18.4%)"]
    shap_explanation = {"volatility": 3.1, "price_change_pct": 2.4}

    async with AsyncPostgresSaver.from_conn_string(settings.langgraph_db_url) as checkpointer:
        await checkpointer.setup()
        graph = build_graph(checkpointer)
        config = {"configurable": {"thread_id": thread_id}}

        await graph.aupdate_state(
            config,
            {
                "request_id": "demo-001",
                "symbol": "XYZ",
                "asset_type": "stock",
                "requested_at": "2026-09-23T00:00:00Z",
                "risk_score": 82.0,
                "risk_factors": risk_factors,
                "fraud_flag": True,
                "fraud_confidence": 0.71,
                "shap_explanation": shap_explanation,
                "requires_human_review": True,
            },
            as_node="fraud_detection",
        )
        await graph.ainvoke(None, config)

    async with async_session() as db:
        db.add(Analysis(
            thread_id=thread_id,
            request_id="demo-001",
            symbol="XYZ",
            asset_type="stock",
            status="pending_review",
            risk_score=82.0,
            risk_factors=risk_factors,
            fraud_flag=True,
            fraud_confidence=0.71,
            shap_explanation=shap_explanation,
            requires_human_review=True,
            requested_by=user.id,
        ))
        await db.commit()

    print(f"Injected paused case + history row: {thread_id}")
    print("Refresh the History page to see it.")


if __name__ == "__main__":
    asyncio.run(main())
