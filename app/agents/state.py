from typing import TypedDict, Optional, Literal, Annotated
import operator


class AgentState(TypedDict):
    # ── Request identity ──────────────────────────────
    request_id: str                     # unique per run — doubles as thread_id
    symbol: str                         # e.g. "AAPL", "BTC-USD"
    asset_type: Literal["stock", "crypto", "forex"]
    requested_at: str                   # ISO timestamp

    # ── Data Collector Agent writes ───────────────────
    raw_market_data: Optional[dict]
    raw_news_data: Optional[list]

    # ── Market Analysis Agent writes ──────────────────
    technical_indicators: Optional[dict]
    market_summary: Optional[str]

    # ── News Intelligence Agent writes ────────────────
    sentiment_score: Optional[float]
    sentiment_summary: Optional[str]

    # ── Risk Assessment Agent writes ──────────────────
    risk_score: Optional[float]
    risk_factors: Optional[list]

    # ── Fraud Detection Agent writes ──────────────────
    fraud_flag: Optional[bool]
    fraud_confidence: Optional[float]
    shap_explanation: Optional[dict]

    # ── Human-in-the-loop control ─────────────────────
    requires_human_review: Optional[bool]
    human_decision: Optional[Literal["approved", "rejected", "pending"]]

    # ── Recommendation & Decision Agent writes ────────
    recommendation: Optional[str]
    decision_rationale: Optional[str]

    # ── Explainability / Report Agent writes ──────────
    final_report: Optional[str]

    # ── Alert & Notification Agent writes ─────────────
    alerts_sent: Annotated[list, operator.add]

    # ── Cross-cutting audit trail ─────────────────────
    agent_log: Annotated[list, operator.add]