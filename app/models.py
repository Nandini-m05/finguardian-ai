from datetime import datetime
from sqlalchemy import String, Boolean, Float, Text, JSON, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(String(50), default="user")


class Analysis(Base):
    """One row per pipeline run - the queryable counterpart to the
    LangGraph checkpoint, which is built for resuming a specific run,
    not for searching or reporting across many.
    """
    __tablename__ = "analyses"

    thread_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64))
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    asset_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), index=True)

    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_factors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    fraud_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fraud_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    shap_explanation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    requires_human_review: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    human_decision: Mapped[str | None] = mapped_column(String(20), nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    decision_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    alerts_sent: Mapped[list | None] = mapped_column(JSON, nullable=True)

    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())