from app.agents.recommendation import compute_recommendation


def test_human_rejection_overrides_everything():
    """The core HITL promise: a human's rejection always wins, even with
    otherwise clean numbers that would normally recommend 'buy'."""
    state = {
        "symbol": "AAPL",
        "risk_score": 5.0,
        "human_decision": "rejected",
        "technical_indicators": {"momentum": "up"},
        "sentiment_score": 0.9,
    }
    recommendation, rationale = compute_recommendation(state)

    assert recommendation == "avoid"
    assert "rejected" in rationale.lower()


def test_high_risk_score_forces_avoid():
    state = {
        "symbol": "XYZ",
        "risk_score": 82.0,
        "human_decision": "approved",
        "technical_indicators": {"momentum": "flat"},
        "sentiment_score": 0.0,
    }
    recommendation, _ = compute_recommendation(state)
    assert recommendation == "avoid"


def test_moderate_risk_holds():
    state = {
        "symbol": "AAPL",
        "risk_score": 41.3,
        "human_decision": "approved",
        "technical_indicators": {"momentum": "up"},
        "sentiment_score": 0.39,
    }
    recommendation, _ = compute_recommendation(state)
    assert recommendation == "hold"


def test_low_risk_strong_positive_signal_buys():
    state = {
        "symbol": "AAPL",
        "risk_score": 15.0,
        "human_decision": "approved",
        "technical_indicators": {"momentum": "up"},
        "sentiment_score": 0.5,
    }
    recommendation, _ = compute_recommendation(state)
    assert recommendation == "buy"


def test_low_risk_strong_negative_signal_avoids():
    state = {
        "symbol": "AAPL",
        "risk_score": 15.0,
        "human_decision": "approved",
        "technical_indicators": {"momentum": "down"},
        "sentiment_score": -0.5,
    }
    recommendation, _ = compute_recommendation(state)
    assert recommendation == "avoid"
