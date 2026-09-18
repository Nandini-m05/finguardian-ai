# FinGuardian AI

An 8-agent, LangGraph-orchestrated financial intelligence backend that analyzes a stock symbol end-to-end — market data, news sentiment, risk scoring, fraud detection, human-in-the-loop review, and an explainable final report — behind a JWT-authenticated FastAPI service.

Built as a B.Tech CSE capstone project.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [Known Environment Notes](#known-environment-notes)
- [Testing](#testing)
- [Roadmap](#roadmap)

## Overview

A client sends `POST /analyze` with a stock symbol. Behind that single request, eight coordinated agents run in sequence — pulling live market and news data, scoring sentiment, assessing risk, detecting fraud signals, pausing for a human reviewer when warranted, deciding on a recommendation, generating a plain-English report, and dispatching an alert if needed. Every run is checkpointed in Postgres via LangGraph, so a paused case survives a server restart and can be resumed hours or days later with a single API call.

## Architecture

```
POST /analyze
      │
      ▼
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  Data Collector  │────▶│  Market Analysis  │────▶│ News Intelligence  │
│ yfinance + Alpha │     │  Technical         │     │  FinBERT sentiment │
│ Vantage News API │     │  indicators        │     │  scoring           │
└─────────────────┘     └──────────────────┘     └───────────────────┘
                                                              │
                                                              ▼
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│ Risk Assessment  │────▶│ Fraud Detection   │────▶│   Human Review     │
│  Rule-based,      │     │ XGBoost +         │     │  interrupt() /     │
│  weighted score    │     │ Isolation Forest  │     │  Command(resume)   │
│  (0-100)           │     │ + SHAP            │     │  when flagged      │
└─────────────────┘     └──────────────────┘     └───────────────────┘
                                                              │
                                                              ▼
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  Recommendation  │────▶│ Explainability /  │────▶│ Alert &            │
│  buy / hold /     │     │ Report            │     │ Notification       │
│  avoid             │     │  Human-readable    │     │  Redis Stream +    │
│                     │     │  synthesis          │     │  Celery → Resend   │
└─────────────────┘     └──────────────────┘     └───────────────────┘
```

**State** flows through all nodes as a single typed `AgentState` (a `TypedDict`), checkpointed to Postgres after every node via `AsyncPostgresSaver`. Fields use LangGraph reducers where they should accumulate (`agent_log`, `alerts_sent`) and plain overwrite where only the latest value matters (`risk_score`, `recommendation`, etc.).

**Human-in-the-loop:** when Fraud Detection flags a case (confident fraud, a gray-zone probability, or disagreement between the two models), the graph genuinely pauses inside `human_review_node` via LangGraph's `interrupt()`. A separate `POST /analyze/{thread_id}/resume` call, carrying an analyst's `approved`/`rejected` decision, resumes that exact paused run from its checkpoint — even across a server restart.

### The eight agents

| # | Agent | Responsibility |
|---|-------|-----------------|
| 1 | Data Collector | Fetches market data (yfinance) and news headlines (Alpha Vantage News & Sentiment), publishes a completion event to Redis Streams |
| 2 | Market Analysis | Computes price change %, 5-day volatility, 5-day range, and momentum from the raw market snapshot |
| 3 | News Intelligence | Scores each article with FinBERT (finance-tuned sentiment model), aggregates to one confidence-weighted sentiment score |
| 4 | Risk Assessment | Combines volatility, sentiment, and momentum into a transparent, rule-based 0–100 risk score with named contributing factors |
| 5 | Fraud Detection | XGBoost (supervised) + Isolation Forest (unsupervised) score the case; SHAP explains which features drove the score; three-outcome framework (clear / flagged / needs human review) |
| 6 | Human Review | Pauses the graph for flagged cases via `interrupt()`; auto-approves clean cases; a human decision always overrides model output |
| 7 | Recommendation & Decision | Synthesizes risk score, momentum, sentiment, and the human decision into a buy / hold / avoid call with rationale |
| 8 | Explainability / Report | Assembles every upstream agent's output into one coherent, human-readable report, translating raw SHAP values into plain language |
| — | Alert & Notification | Decides alert severity (critical / warning / none), publishes an audit-trail event to Redis Streams, and dispatches a Celery task that sends a real email via Resend |

## Tech Stack

- **API:** FastAPI, Uvicorn, Nginx (reverse proxy + rate limiting)
- **Agent orchestration:** LangGraph, with Postgres-backed checkpointing (`AsyncPostgresSaver`)
- **Auth:** JWT (python-jose) + bcrypt password hashing, role-based access control
- **Database:** PostgreSQL (`pgvector/pgvector` image) — one instance serving both the application schema (via SQLAlchemy async + Alembic) and LangGraph's own checkpoint tables
- **Event bus / cache:** Redis Streams (audit trail for Data Collector and Alert events), also the Celery broker/backend
- **Background tasks:** Celery (alert delivery)
- **ML/AI:**
  - FinBERT (`ProsusAI/finbert` via HuggingFace `transformers`) — news sentiment
  - XGBoost + scikit-learn `IsolationForest` — fraud/anomaly detection
  - SHAP — model explainability
- **External data:** yfinance, Alpha Vantage News & Sentiment API
- **Email delivery:** Resend
- **Infra:** Docker Compose (Postgres, Redis, Nginx containers)

## Project Structure

```
finguardian-ai/
├── alembic/
│   ├── versions/            # migration history
│   └── env.py                # excludes LangGraph's checkpoint tables from autogenerate
├── app/
│   ├── agents/
│   │   ├── state.py           # shared AgentState TypedDict
│   │   ├── data_collector.py
│   │   ├── market_analysis.py
│   │   ├── news_intelligence.py
│   │   ├── risk_assessment.py
│   │   ├── fraud_features.py  # fraud_detection_node lives here
│   │   ├── human_review.py
│   │   ├── recommendation.py
│   │   ├── report.py
│   │   └── alert_notification.py
│   ├── events/
│   │   └── redis_client.py    # shared Redis client + publish_event()
│   ├── graph.py                # single source of truth for graph wiring
│   ├── main.py                 # FastAPI app, routes, lifespan
│   ├── celery_app.py
│   ├── tasks.py                # deliver_alert Celery task
│   ├── config.py                # pydantic-settings
│   ├── database.py
│   ├── models.py                # SQLAlchemy models (User, Analysis)
│   ├── schemas.py                # Pydantic request/response models
│   ├── security.py
│   └── dependencies.py           # get_current_user, require_role
├── nginx/
│   └── nginx.conf                # rate limiting + reverse proxy
├── docker-compose.yml
├── requirements.txt
└── .env                          # not committed
```

## Prerequisites

- Python 3.11
- Docker Desktop
- Git
- A free [Alpha Vantage](https://www.alphavantage.co/support/#api-key) API key (25 requests/day)
- A free [Resend](https://resend.com/signup) API key

## Setup

```bash
git clone https://github.com/Nandini-m05/finguardian-ai.git
cd finguardian-ai

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

Create a `.env` file in the project root (see [Environment Variables](#environment-variables) below).

Start the containers and apply migrations:

```bash
docker compose up -d
alembic upgrade head
```

## Environment Variables

| Variable | Required | Notes |
|---|---|---|
| `APP_ENV` | No (default `development`) | |
| `DATABASE_URL` | Yes | Main application Postgres connection string |
| `LANGGRAPH_DB_URL` | Yes | Postgres connection string for LangGraph checkpointing — **must** be psycopg-style (`postgresql://...`), not `+asyncpg` |
| `JWT_SECRET` | Yes | |
| `JWT_ALGORITHM` | No (default `HS256`) | |
| `JWT_EXPIRE_MINUTES` | No (default `60`) | |
| `REDIS_URL` | No (default `redis://localhost:6379`) | |
| `ALPHA_VANTAGE_API_KEY` | Yes | Free tier: 25 requests/day |
| `RESEND_API_KEY` | Yes | |
| `ALERT_RECIPIENT_EMAIL` | Yes | Until a custom domain is verified with Resend, this must be the email address the Resend account was created with |

## Running the Application

This runs as three separate long-lived processes, each in its own terminal.

**1. Postgres, Redis, and Nginx** (via Docker Compose — see [Setup](#setup))

**2. The API server:**

```bash
uvicorn app.main:app --reload
```

**3. The Celery worker** (for alert delivery):

```bash
celery -A app.celery_app worker --loglevel=info --pool=solo
```

> `--pool=solo` is required on Windows, where Celery's default `fork()`-based pool isn't available.

The API is then reachable directly at `http://localhost:8000`, or through the Nginx reverse proxy (with rate limiting applied) at `http://localhost:8080`.

## API Reference

Interactive docs are available at `http://localhost:8000/docs` (Swagger UI).

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/register` | No | Create a user account |
| `POST` | `/login` | No | Returns a JWT access token |
| `GET` | `/me` | Yes | Current user info |
| `POST` | `/analyze` | Yes (rate-limited: 5/min) | Run the full 8-agent pipeline for a symbol |
| `POST` | `/analyze/{thread_id}/resume` | Yes | Submit a human reviewer's decision for a paused analysis |
| `GET` | `/health` | No | Health check |

Authenticated requests use a standard bearer token header: `Authorization: Bearer <token>`.

**Example — running an analysis:**

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "asset_type": "stock"}'
```

```json
{
  "request_id": "req-1527570d",
  "thread_id": "analysis-f43a93f8",
  "status": "completed",
  "symbol": "AAPL",
  "risk_score": 27.9,
  "risk_factors": ["Elevated price volatility (2.63)"],
  "fraud_flag": false,
  "fraud_confidence": 0.001,
  "requires_human_review": false,
  "human_decision": "approved",
  "recommendation": "buy",
  "decision_rationale": "AAPL: risk score 27.9/100, up momentum, sentiment +0.19 -> recommendation: buy.",
  "final_report": "FinGuardian AI Report - AAPL\n...",
  "alerts_sent": []
}
```

When a case is flagged, `status` comes back as `"pending_review"` instead, and the same `thread_id` is submitted to the resume endpoint along with `{"decision": "approved"}` or `{"decision": "rejected"}` once a human has reviewed it.

## Known Environment Notes

A few non-obvious things worth knowing if you're setting this up fresh, particularly on Windows:

- **`WindowsSelectorEventLoopPolicy`** is required before any `asyncio` code runs — `psycopg`'s async driver isn't compatible with Windows' default `ProactorEventLoop`.
- **Windows Smart App Control**, if enabled, can block newly-installed compiled Python packages (e.g. after installing `torch`) with an `Application Control policy has blocked this file` error. Disabling it is a one-way setting change (re-enabling later requires a full Windows reset).
- **Alembic + LangGraph coexistence:** LangGraph's `AsyncPostgresSaver.setup()` creates its checkpoint tables directly, outside SQLAlchemy. Without the `include_object` filter already present in `alembic/env.py`, running `alembic revision --autogenerate` would detect those tables as "removed" and generate a migration that drops them.
- **Celery workers don't hot-reload.** Unlike `uvicorn --reload`, a running worker must be manually restarted to pick up changes to `tasks.py`.
- Alpha Vantage's free tier is capped at 25 requests/day — during development, prefer resuming an existing LangGraph checkpoint (`aget_state` / `aupdate_state`) over re-running the full pipeline where possible.

## Testing

Verification so far has been done through targeted scripts (`app/test_*.py`) exercising each agent individually and in combination, plus manual end-to-end testing via Swagger. A `pytest` suite covering the core agents and API routes is planned as follow-up work.

## Roadmap

- [ ] Automated `pytest` test suite
- [ ] MinIO integration for storing generated reports/filings
- [ ] Observability stack (Prometheus, Grafana, OpenTelemetry, Loki)
- [ ] Custom domain verification with Resend (removes the single-recipient sandbox restriction)
