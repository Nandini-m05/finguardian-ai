import streamlit as st
from common import require_login

st.set_page_config(page_title="How It Works - FinGuardian AI", page_icon=":information_source:", layout="centered")
require_login()

st.title("How FinGuardian AI Works")

st.write(
    "Every analysis runs through eight coordinated AI agents, in sequence, "
    "orchestrated by LangGraph. Each agent reads what the previous ones already "
    "found and adds its own piece."
)

st.write("---")

steps = [
    ("1. Data Collector", "Pulls live market data (yfinance) and recent news headlines (Alpha Vantage) for the symbol."),
    ("2. Market Analysis", "Computes price change %, 5-day volatility, trading range, and momentum from the raw market data."),
    ("3. News Intelligence", "Scores each news article with FinBERT, a finance-tuned sentiment model, and combines them into one confidence-weighted sentiment score."),
    ("4. Risk Assessment", "Combines volatility, sentiment, and momentum into a transparent, rule-based 0-100 risk score with named contributing factors."),
    ("5. Fraud Detection", "Two ML models -- XGBoost and Isolation Forest -- independently assess the case. SHAP explains exactly which features drove the score."),
    ("6. Human Review", "If the case is flagged (confident fraud signal, a borderline score, or the two models disagreeing), the pipeline genuinely pauses here until a person approves or rejects it. A human's decision always overrides the model."),
    ("7. Recommendation", "Combines the risk score, momentum, sentiment, and the human decision (if any) into one buy / hold / avoid call."),
    ("8. Explainability / Report", "Assembles everything above into the plain-English report you see for each analysis."),
    ("+ Alert and Notification", "Decides whether this case warrants an alert (critical / warning / none) and, if so, dispatches it."),
]

for title, desc in steps:
    st.markdown(f"**{title}**")
    st.write(desc)
    st.write("")

st.write("---")
st.subheader("About alerts")
st.info(
    "Alerts are currently routed to a single monitoring email address configured "
    "for this deployment, not to each individual user's own inbox -- this build "
    "demonstrates the alerting mechanism itself (Redis Streams for a durable audit "
    "trail, plus a real email dispatched via Resend) rather than per-user delivery. "
    "A warning alert fires when a case is recommended AVOID or scores 60+ on risk; "
    "a critical alert fires when fraud is confirmed, or a human reviewer rejects a case."
)
