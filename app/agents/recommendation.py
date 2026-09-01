from app.agents.state import AgentState


def compute_recommendation(state: dict) -> tuple[str, str]:
    """Synthesize risk, sentiment, and momentum into one call - with a human's
    decision always taking precedence over the numbers, never the reverse.
    """
    symbol = state.get("symbol")
    risk_score = state.get("risk_score") or 0
    human_decision = state.get("human_decision")
    momentum = (state.get("technical_indicators") or {}).get("momentum", "flat")
    sentiment_score = state.get("sentiment_score") or 0

    if human_decision == "rejected":
        return "avoid", f"{symbol}: a human reviewer rejected this case - overriding all other signals."

    if risk_score >= 60:
        recommendation = "avoid"
    elif risk_score >= 30:
        recommendation = "hold"
    elif momentum == "up" and sentiment_score > 0.15:
        recommendation = "buy"
    elif momentum == "down" and sentiment_score < -0.15:
        recommendation = "avoid"
    else:
        recommendation = "hold"

    rationale = (
        f"{symbol}: risk score {risk_score}/100, {momentum} momentum, "
        f"sentiment {sentiment_score:+.2f} -> recommendation: {recommendation}."
    )
    if human_decision == "approved" and state.get("requires_human_review"):
        rationale += " (Manually reviewed and approved despite elevated risk signals.)"

    return recommendation, rationale


def recommendation_node(state: AgentState) -> dict:
    """LangGraph node: Recommendation & Decision Agent."""
    symbol = state["symbol"]

    if state.get("risk_score") is None:
        return {
            "agent_log": [f"[Recommendation] Skipped - missing upstream data for {symbol}"],
        }

    recommendation, rationale = compute_recommendation(state)

    return {
        "recommendation": recommendation,
        "decision_rationale": rationale,
        "agent_log": [f"[Recommendation] {rationale}"],
    }