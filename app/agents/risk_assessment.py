from app.agents.state import AgentState


def compute_risk_score(technical_indicators: dict, sentiment_score: float) -> tuple[float, list[str]]:
    """Combine technical and sentiment signals into a single rule-based risk score (0-100).

    v1 is intentionally rule-based and transparent rather than ML-driven -
    that keeps it explainable, which the Explainability/Report agent will
    lean on later. Heavier ML (XGBoost, Isolation Forest) is reserved for
    Fraud Detection specifically, per the architecture.
    """
    factors = []
    score = 0.0

    volatility = technical_indicators.get("volatility") or 0
    volatility_points = min(volatility * 10, 40)
    score += volatility_points
    if volatility_points > 15:
        factors.append(f"Elevated price volatility ({volatility})")

    if sentiment_score < 0:
        sentiment_points = min(abs(sentiment_score) * 30, 30)
        score += sentiment_points
        if sentiment_points > 10:
            factors.append(f"Negative news sentiment ({sentiment_score:+.2f})")

    price_change_pct = technical_indicators.get("price_change_pct") or 0
    momentum_points = min(abs(price_change_pct) * 5, 20)
    score += momentum_points
    if momentum_points > 10:
        factors.append(f"Large single-day price move ({price_change_pct:+.2f}%)")

    if not factors:
        factors.append("No significant risk signals detected")

    return round(min(score, 100), 1), factors


def risk_assessment_node(state: AgentState) -> dict:
    """LangGraph node: Risk Assessment Agent."""
    symbol = state["symbol"]
    technical_indicators = state.get("technical_indicators")
    sentiment_score = state.get("sentiment_score")

    if technical_indicators is None or sentiment_score is None:
        return {
            "agent_log": [f"[RiskAssessment] Skipped - missing upstream data for {symbol}"],
        }

    risk_score, risk_factors = compute_risk_score(technical_indicators, sentiment_score)

    return {
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "agent_log": [f"[RiskAssessment] {symbol} risk score: {risk_score}/100 - {', '.join(risk_factors)}"],
    }