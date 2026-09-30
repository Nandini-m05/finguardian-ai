from pydantic import BaseModel, EmailStr
from typing import Literal
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    is_active: bool
    role: str

    class Config:
        from_attributes = True


class AnalysisRequest(BaseModel):
    symbol: str
    asset_type: Literal["stock", "crypto", "forex"] = "stock"


class AnalysisResponse(BaseModel):
    request_id: str
    thread_id: str
    status: Literal["completed", "pending_review"]
    symbol: str
    risk_score: float | None = None
    risk_factors: list[str] | None = None
    fraud_flag: bool | None = None
    fraud_confidence: float | None = None
    shap_explanation: dict | None = None
    requires_human_review: bool | None = None
    human_decision: str | None = None
    recommendation: str | None = None
    decision_rationale: str | None = None
    final_report: str | None = None
    alerts_sent: list = []


class ResumeDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]


class AnalysisSummary(BaseModel):
    thread_id: str
    symbol: str
    status: str
    risk_score: float | None = None
    recommendation: str | None = None
    requires_human_review: bool | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class AdminPendingReview(BaseModel):
    thread_id: str
    symbol: str
    risk_score: float | None = None
    fraud_flag: bool | None = None
    fraud_confidence: float | None = None
    requested_by_email: str
    created_at: datetime
