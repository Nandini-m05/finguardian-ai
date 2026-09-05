from datetime import datetime, timezone
from app.agents.state import AgentState
from app.events.redis_client import publish_event
from app.tasks import deliver_alert

ALERTS_STREAM = "alert_events"


def determine_alert(state: dict) -> dict | None:
    """Decide whether this case warrants an alert, and at what severity.

    This agent decides AND records an alert - it doesn't send one. Real
    delivery (email/SMS/Slack) is deferred to a future Celery worker that
    consumes this same Redis Stream.
    """
    symbol = state.get("symbol")
    fraud_flag = state.get("fraud_flag")
    human_decision = state.get("human_decision")
    recommendation = state.get("recommendation")
    risk_score = state.get("risk_score") or 0

    if fraud_flag or human_decision == "rejected":
        severity = "critical"
        reason = "Fraud signal confirmed or case rejected in human review"
    elif recommendation == "avoid" or risk_score >= 60:
        severity = "warning"
        reason = f"Recommendation is '{recommendation}' or risk score elevated ({risk_score})"
    else:
        return None

    return {
        "symbol": symbol,
        "severity": severity,
        "reason": reason,
        "risk_score": risk_score,
        "recommendation": recommendation,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
    }


async def alert_notification_node(state: AgentState) -> dict:
    """LangGraph node: Alert & Notification Agent."""
    symbol = state["symbol"]
    alert = determine_alert(state)

    if alert is None:
        return {
            "agent_log": [f"[AlertNotification] No alert warranted for {symbol}"],
        }

    await publish_event(ALERTS_STREAM, {
        "symbol": alert["symbol"],
        "severity": alert["severity"],
        "reason": alert["reason"],
        "risk_score": str(alert["risk_score"]),
        "recommendation": alert["recommendation"] or "",
        "triggered_at": alert["triggered_at"],
    })
    # Redis Stream above is the durable audit trail. This is the separate
    # handoff to Celery for actual delivery - fire-and-forget, doesn't
    # block the graph waiting for the worker to pick it up.
    deliver_alert.delay(alert)
    return {
        "alerts_sent": [alert],
        "agent_log": [f"[AlertNotification] {alert['severity'].upper()} alert for {symbol}: {alert['reason']}"],
    }

