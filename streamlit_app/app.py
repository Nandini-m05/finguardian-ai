import os
import requests
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="FinGuardian AI", page_icon="chart", layout="centered")

if "token" not in st.session_state:
    st.session_state.token = None
if "email" not in st.session_state:
    st.session_state.email = None


def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


def login(email, password):
    resp = requests.post(f"{API_BASE_URL}/login", json={"email": email, "password": password})
    if resp.status_code == 200:
        st.session_state.token = resp.json()["access_token"]
        st.session_state.email = email
        return True, None
    return False, resp.json().get("detail", "Login failed")


def register(email, password):
    resp = requests.post(f"{API_BASE_URL}/register", json={"email": email, "password": password})
    if resp.status_code == 200:
        return True, None
    return False, resp.json().get("detail", "Registration failed")


def run_analysis(symbol):
    return requests.post(
        f"{API_BASE_URL}/analyze",
        json={"symbol": symbol, "asset_type": "stock"},
        headers=auth_headers(),
        timeout=60,
    )


def resume_analysis(thread_id, decision):
    return requests.post(
        f"{API_BASE_URL}/analyze/{thread_id}/resume",
        json={"decision": decision},
        headers=auth_headers(),
        timeout=60,
    )


def handle_resume_response(resp):
    if resp.status_code == 200:
        st.success("Decision submitted.")
        render_result(resp.json())
    else:
        st.error(f"Failed to submit decision: {resp.text}")


def render_result(result):
    st.subheader(f"{result['symbol']} -- {result['status'].replace('_', ' ').title()}")
    risk_score = result.get("risk_score")

    if result["status"] == "pending_review":
        st.warning("This case was flagged and needs human review before a final recommendation.")
        col1, col2, col3 = st.columns(3)
        col1.metric("Risk Score", f"{risk_score}/100" if risk_score is not None else "N/A")
        conf = result.get("fraud_confidence")
        col2.metric("Fraud Confidence", f"{conf:.1%}" if conf is not None else "N/A")
        col3.metric("Fraud Flag", "Yes" if result.get("fraud_flag") else "No")

        if result.get("risk_factors"):
            st.write("**Risk factors:**")
            for factor in result["risk_factors"]:
                st.write(f"- {factor}")

        if result.get("shap_explanation"):
            st.write("**Model explanation (SHAP):**")
            st.json(result["shap_explanation"])

        st.write("---")
        st.write("**Analyst decision:**")
        c1, c2 = st.columns(2)
        if c1.button("Approve", key=f"approve-{result['thread_id']}", type="primary"):
            handle_resume_response(resume_analysis(result["thread_id"], "approved"))
        if c2.button("Reject", key=f"reject-{result['thread_id']}"):
            handle_resume_response(resume_analysis(result["thread_id"], "rejected"))
        return

    rec = (result.get("recommendation") or "").upper()
    rec_marker = {"BUY": "[BUY]", "HOLD": "[HOLD]", "AVOID": "[AVOID]"}.get(rec, "")
    st.markdown(f"### {rec_marker} Recommendation: **{rec or 'N/A'}**")

    col1, col2, col3 = st.columns(3)
    col1.metric("Risk Score", f"{risk_score}/100" if risk_score is not None else "N/A")
    col2.metric("Human Decision", result.get("human_decision") or "N/A")
    col3.metric("Fraud Flag", "Yes" if result.get("fraud_flag") else "No")

    for alert in (result.get("alerts_sent") or []):
        st.error(f"{alert['severity'].upper()} ALERT: {alert['reason']}")

    with st.expander("Full report", expanded=True):
        st.text(result.get("final_report") or "No report available.")

    with st.expander("Raw response"):
        st.json(result)


if not st.session_state.token:
    st.title("FinGuardian AI")
    st.caption("Multi-agent financial intelligence backend - log in to run an analysis.")

    tab_login, tab_register = st.tabs(["Log In", "Register"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log In"):
                ok, error = login(email, password)
                if ok:
                    st.rerun()
                else:
                    st.error(error)

    with tab_register:
        with st.form("register_form"):
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Password", type="password", key="reg_password")
            if st.form_submit_button("Register"):
                ok, error = register(email, password)
                if ok:
                    st.success("Account created - you can log in now.")
                else:
                    st.error(error)

else:
    st.title("FinGuardian AI")
    col1, col2 = st.columns([4, 1])
    col1.caption(f"Logged in as {st.session_state.email}")
    if col2.button("Log out"):
        st.session_state.token = None
        st.session_state.email = None
        st.rerun()

    st.write("---")

    symbol = st.text_input("Stock symbol", value="AAPL", max_chars=10).upper().strip()
    st.caption("Each analysis uses a real, limited external API call (25/day) - avoid re-running the same symbol unnecessarily.")

    if st.button("Analyze", type="primary", disabled=not symbol):
        with st.spinner(f"Running the 8-agent pipeline for {symbol}... this can take 10-20 seconds."):
            resp = run_analysis(symbol)

        if resp.status_code == 200:
            render_result(resp.json())
        elif resp.status_code == 429:
            st.error("Rate limit reached (5 analyses/minute). Please wait a moment and try again.")
        elif resp.status_code in (401, 403):
            st.error("Session expired - please log out and log back in.")
        else:
            st.error(f"Request failed ({resp.status_code}): {resp.text}")

