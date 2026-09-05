from app.celery_app import celery_app

@celery_app.task
def ping() -> str:
    return "pong"


@celery_app.task(name="deliver_alert")
def deliver_alert(alert: dict) -> dict:
    """Deliver a single alert. Placeholder for a real provider (SendGrid,
    Twilio, etc.) - the point of this task is proving the async handoff
    works; swapping in a real provider later won't change anything about
    how alert_notification_node calls this.
    """
    print(
        f"[ALERT DELIVERY] {alert['severity'].upper()} - {alert['symbol']}: "
        f"{alert['reason']} (risk_score={alert['risk_score']})"
    )
    return {"delivered": True, "symbol": alert["symbol"], "severity": alert["severity"]}