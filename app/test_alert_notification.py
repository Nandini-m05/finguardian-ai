import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.agents.alert_notification import alert_notification_node
from app.events.redis_client import get_redis_client


async def main():
    clean_state = {
        "symbol": "AAPL",
        "fraud_flag": False,
        "human_decision": "approved",
        "recommendation": "hold",
        "risk_score": 41.3,
    }
    flagged_state = {
        "symbol": "XYZ",
        "fraud_flag": True,
        "human_decision": "approved",
        "recommendation": "avoid",
        "risk_score": 78.0,
    }

    print("--- Clean case (should produce no alert) ---")
    result1 = await alert_notification_node(clean_state)
    print(result1)

    print("\n--- Flagged case (should produce a critical alert) ---")
    result2 = await alert_notification_node(flagged_state)
    print(result2)

    redis_client = get_redis_client()
    entries = await redis_client.xrange("alert_events", count=5)
    print("\nLatest entries on alert_events stream:")
    for entry_id, fields in entries:
        print(f"  {entry_id}: {fields}")
    await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())