from langgraph.types import interrupt
from app.agents.state import AgentState


def human_review_node(state: AgentState) -> dict:
    """LangGraph node: pauses the graph for a real human decision when flagged.

    Cases that never needed review are marked 'approved' by default, so
    downstream agents can treat 'approved' uniformly as "clear to proceed" -
    regardless of whether that came from a person or was auto-cleared.
    """
    symbol = state["symbol"]

    if not state.get("requires_human_review"):
        return {
            "human_decision": "approved",
            "agent_log": [f"[HumanReview] No review required for {symbol} - auto-approved"],
        }

    # Execution genuinely pauses here, checkpointed in Postgres. Whatever a
    # caller later passes via Command(resume=...) becomes this call's return
    # value when the graph resumes - even if that happens minutes, hours,
    # or a server restart later.
    decision = interrupt({
        "symbol": symbol,
        "risk_score": state.get("risk_score"),
        "fraud_confidence": state.get("fraud_confidence"),
        "risk_factors": state.get("risk_factors"),
        "shap_explanation": state.get("shap_explanation"),
        "message": f"{symbol} flagged for review - approve or reject.",
    })

    return {
        "human_decision": decision,
        "agent_log": [f"[HumanReview] {symbol} - human decision: {decision}"],
    }