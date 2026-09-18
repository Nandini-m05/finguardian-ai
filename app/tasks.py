import resend
from app.config import settings
from app.celery_app import celery_app

resend.api_key = settings.resend_api_key


@celery_app.task
def ping() -> str:
    return "pong"


@celery_app.task(name="deliver_alert")
def deliver_alert(alert: dict) -> dict:
    """Deliver a single alert via Resend. A failed send never crashes the
    task or the worker - the durable record already exists in Redis
    Streams (written before this task runs), so a delivery failure here
    is recoverable, not a pipeline failure.
    """
    subject = "[FinGuardian AI] " + alert["severity"].upper() + " Alert - " + alert["symbol"]
    html = (
        "<h2>" + alert["severity"].upper() + " Alert: " + alert["symbol"] + "</h2>"
        + "<p><strong>Reason:</strong> " + alert["reason"] + "</p>"
        + "<p><strong>Risk score:</strong> " + str(alert["risk_score"]) + "/100</p>"
        + "<p><strong>Recommendation:</strong> " + str(alert.get("recommendation") or "N/A").upper() + "</p>"
        + "<p><strong>Triggered at:</strong> " + alert["triggered_at"] + "</p>"
    )

    try:
        response = resend.Emails.send({
            "from": "FinGuardian AI <onboarding@resend.dev>",
            "to": settings.alert_recipient_email,
            "subject": subject,
            "html": html,
        })
        print("[ALERT DELIVERY] Sent via Resend, id: " + str(response.get("id")))
        return {"delivered": True, "symbol": alert["symbol"], "severity": alert["severity"], "email_id": response.get("id")}
    except Exception as e:
        print("[ALERT DELIVERY] FAILED for " + alert["symbol"] + ": " + str(e))
        return {"delivered": False, "symbol": alert["symbol"], "severity": alert["severity"], "error": str(e)}
