from app.agents.alert_notification import determine_alert


def test_fraud_flag_triggers_critical():
    state = {"symbol": "XYZ", "fraud_flag": True, "human_decision": "approved",
             "recommendation": "avoid", "risk_score": 82.0}
    alert = determine_alert(state)
    assert alert["severity"] == "critical"


def test_human_rejection_triggers_critical():
    state = {"symbol": "XYZ", "fraud_flag": False, "human_decision": "rejected",
             "recommendation": "avoid", "risk_score": 40.0}
    alert = determine_alert(state)
    assert alert["severity"] == "critical"


def test_high_risk_avoid_triggers_warning():
    state = {"symbol": "AAPL", "fraud_flag": False, "human_decision": "approved",
             "recommendation": "avoid", "risk_score": 65.0}
    alert = determine_alert(state)
    assert alert["severity"] == "warning"


def test_clean_case_triggers_no_alert():
    state = {"symbol": "AAPL", "fraud_flag": False, "human_decision": "approved",
             "recommendation": "hold", "risk_score": 41.3}
    alert = determine_alert(state)
    assert alert is None
