import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uuid
from contextlib import asynccontextmanager, AsyncExitStack
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import async_session, get_db
from app.models import User, Analysis
from app.schemas import UserCreate, UserOut, AnalysisRequest, AnalysisResponse, ResumeDecisionRequest, AnalysisSummary, AdminPendingReview
from app.security import hash_password, verify_password, create_access_token
from app.dependencies import get_current_user, require_role
from app.graph import build_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        checkpointer = await stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(settings.langgraph_db_url)
        )
        await checkpointer.setup()
        app.state.graph = build_graph(checkpointer)
        yield


app = FastAPI(lifespan=lifespan)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/")
def read_root():
    return {"message": "Hello! Your FinGuardian AI backend is alive."}

@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.app_env}

@app.get("/db-check")
async def db_check():
    async with async_session() as session:
        result = await session.execute(text("SELECT 1"))
        value = result.scalar()
    return {"database": "connected", "result": value}

@app.post("/register", response_model=UserOut)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user

@app.post("/login")
async def login(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=UserOut)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/admin-only")
async def admin_only_route(current_user: User = Depends(require_role("admin"))):
    return {"message": f"Welcome, admin {current_user.email}"}


def _build_analysis_response(request_id: str, thread_id: str, symbol: str, result: dict) -> AnalysisResponse:
    is_paused = "__interrupt__" in result
    return AnalysisResponse(
        request_id=request_id,
        thread_id=thread_id,
        status="pending_review" if is_paused else "completed",
        symbol=symbol,
        risk_score=result.get("risk_score"),
        risk_factors=result.get("risk_factors"),
        fraud_flag=result.get("fraud_flag"),
        fraud_confidence=result.get("fraud_confidence"),
        shap_explanation=result.get("shap_explanation"),
        requires_human_review=result.get("requires_human_review"),
        human_decision=result.get("human_decision"),
        recommendation=result.get("recommendation"),
        decision_rationale=result.get("decision_rationale"),
        final_report=result.get("final_report"),
        alerts_sent=result.get("alerts_sent") or [],
    )


async def _save_analysis_record(db: AsyncSession, response: AnalysisResponse, requested_by: int | None) -> None:
    """Upsert one row per thread_id - insert on first save (often
    'pending_review'), update that same row on resume (now 'completed').
    requested_by is only used on insert; the update branch never touches
    it, so passing the resuming admin's id here on a resume is harmless -
    the original requester is preserved automatically."""
    existing = await db.get(Analysis, response.thread_id)

    if existing is None:
        record = Analysis(
            thread_id=response.thread_id,
            request_id=response.request_id,
            symbol=response.symbol,
            asset_type="stock",
            status=response.status,
            risk_score=response.risk_score,
            risk_factors=response.risk_factors,
            fraud_flag=response.fraud_flag,
            fraud_confidence=response.fraud_confidence,
            shap_explanation=response.shap_explanation,
            requires_human_review=response.requires_human_review,
            human_decision=response.human_decision,
            recommendation=response.recommendation,
            decision_rationale=response.decision_rationale,
            final_report=response.final_report,
            alerts_sent=response.alerts_sent,
            requested_by=requested_by,
        )
        db.add(record)
    else:
        existing.status = response.status
        existing.risk_score = response.risk_score
        existing.risk_factors = response.risk_factors
        existing.fraud_flag = response.fraud_flag
        existing.fraud_confidence = response.fraud_confidence
        existing.shap_explanation = response.shap_explanation
        existing.requires_human_review = response.requires_human_review
        existing.human_decision = response.human_decision
        existing.recommendation = response.recommendation
        existing.decision_rationale = response.decision_rationale
        existing.final_report = response.final_report
        existing.alerts_sent = response.alerts_sent

    await db.commit()


@app.post("/analyze", response_model=AnalysisResponse)
@limiter.limit("5/minute")
async def analyze_symbol(
    payload: AnalysisRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    graph = request.app.state.graph
    request_id = f"req-{uuid.uuid4().hex[:8]}"
    thread_id = f"analysis-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "request_id": request_id,
        "symbol": payload.symbol.upper(),
        "asset_type": payload.asset_type,
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }

    result = await graph.ainvoke(initial_state, config)
    response = _build_analysis_response(request_id, thread_id, payload.symbol.upper(), result)
    await _save_analysis_record(db, response, current_user.id)
    return response


@app.post("/analyze/{thread_id}/resume", response_model=AnalysisResponse)
async def resume_analysis(
    thread_id: str,
    payload: ResumeDecisionRequest,
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: a human's decision always overrides the model, and only
    an admin/analyst account - never the user who triggered the analysis -
    can supply that decision. An admin also cannot review their own
    submission, even if they hold the admin role - separation of duties."""
    record = await db.get(Analysis, thread_id)
    if record is not None and record.requested_by == current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot review your own submission. Ask another admin to review this case.",
        )

    graph = request.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}

    state = await graph.aget_state(config)
    if not state.next:
        raise HTTPException(status_code=400, detail="This analysis is not currently paused for review.")

    result = await graph.ainvoke(Command(resume=payload.decision), config)

    symbol = state.values.get("symbol", "UNKNOWN")
    request_id = state.values.get("request_id", "unknown")
    response = _build_analysis_response(request_id, thread_id, symbol, result)
    await _save_analysis_record(db, response, current_user.id)
    return response


@app.get("/analyses", response_model=list[AnalysisSummary])
async def list_my_analyses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the current user's own analysis history, most recent first."""
    result = await db.execute(
        select(Analysis)
        .where(Analysis.requested_by == current_user.id)
        .order_by(Analysis.created_at.desc())
    )
    return result.scalars().all()


@app.get("/analyses/{thread_id}", response_model=AnalysisResponse)
async def get_analysis_detail(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns full detail for an analysis - the requester's own, or any
    analysis at all if the current user is an admin."""
    record = await db.get(Analysis, thread_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if record.requested_by != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=404, detail="Analysis not found")

    return AnalysisResponse(
        request_id=record.request_id,
        thread_id=record.thread_id,
        status=record.status,
        symbol=record.symbol,
        risk_score=record.risk_score,
        risk_factors=record.risk_factors,
        fraud_flag=record.fraud_flag,
        fraud_confidence=record.fraud_confidence,
        shap_explanation=record.shap_explanation,
        requires_human_review=record.requires_human_review,
        human_decision=record.human_decision,
        recommendation=record.recommendation,
        decision_rationale=record.decision_rationale,
        final_report=record.final_report,
        alerts_sent=record.alerts_sent or [],
    )


@app.get("/admin/pending-reviews", response_model=list[AdminPendingReview])
async def list_pending_reviews(
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: every OTHER user's cases currently awaiting review,
    oldest first. Deliberately excludes the current admin's own
    submissions - an admin reviewing their own flagged case would defeat
    the separation-of-duties this role exists to enforce."""
    result = await db.execute(
        select(Analysis, User.email)
        .join(User, Analysis.requested_by == User.id)
        .where(Analysis.status == "pending_review")
        .where(Analysis.requested_by != current_user.id)
        .order_by(Analysis.created_at.asc())
    )
    return [
        AdminPendingReview(
            thread_id=a.thread_id,
            symbol=a.symbol,
            risk_score=a.risk_score,
            fraud_flag=a.fraud_flag,
            fraud_confidence=a.fraud_confidence,
            requested_by_email=email,
            created_at=a.created_at,
        )
        for a, email in result.all()
    ]
