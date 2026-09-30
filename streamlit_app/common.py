import os
import requests
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


def init_session_state():
    if "token" not in st.session_state:
        st.session_state.token = None
    if "email" not in st.session_state:
        st.session_state.email = None
    if "role" not in st.session_state:
        st.session_state.role = None


def require_login():
    init_session_state()
    if not st.session_state.token:
        st.warning("Please log in from the Home page first.")
        st.stop()


def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


def login(email, password):
    resp = requests.post(f"{API_BASE_URL}/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        return False, resp.json().get("detail", "Login failed")

    st.session_state.token = resp.json()["access_token"]
    st.session_state.email = email

    me_resp = requests.get(f"{API_BASE_URL}/me", headers=auth_headers())
    st.session_state.role = me_resp.json().get("role", "user") if me_resp.status_code == 200 else "user"

    return True, None


def register(email, password):
    resp = requests.post(f"{API_BASE_URL}/register", json={"email": email, "password": password})
    if resp.status_code == 200:
        return True, None
    return False, resp.json().get("detail", "Registration failed")


def logout():
    st.session_state.token = None
    st.session_state.email = None
    st.session_state.role = None


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


def list_analyses():
    return requests.get(f"{API_BASE_URL}/analyses", headers=auth_headers(), timeout=30)


def get_analysis_detail(thread_id):
    return requests.get(f"{API_BASE_URL}/analyses/{thread_id}", headers=auth_headers(), timeout=30)


def list_pending_reviews():
    return requests.get(f"{API_BASE_URL}/admin/pending-reviews", headers=auth_headers(), timeout=30)


RECOMMENDATION_COLORS = {"BUY": "green", "HOLD": "orange", "AVOID": "red"}


def recommendation_badge(rec):
    rec = (rec or "N/A").upper()
    color = RECOMMENDATION_COLORS.get(rec, "gray")
    return f":{color}[**{rec}**]"


def render_result(result, allow_review=False):
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
        can_review = allow_review and st.session_state.get("role") == "admin"
        if can_review:
            st.write("**Analyst decision:**")
            c1, c2 = st.columns(2)
            if c1.button("Approve", key=f"approve-{result['thread_id']}", type="primary"):
                resp = resume_analysis(result["thread_id"], "approved")
                if resp.status_code == 200:
                    st.success("Decision submitted.")
                    render_result(resp.json(), allow_review=allow_review)
                else:
                    st.error(f"Failed to submit decision: {resp.text}")
            if c2.button("Reject", key=f"reject-{result['thread_id']}"):
                resp = resume_analysis(result["thread_id"], "rejected")
                if resp.status_code == 200:
                    st.success("Decision submitted.")
                    render_result(resp.json(), allow_review=allow_review)
                else:
                    st.error(f"Failed to submit decision: {resp.text}")
        elif not allow_review:
            st.info("You submitted this case yourself, so it can't be reviewed here. Another admin needs to approve or reject it.")
        else:
            st.info("This case is awaiting review by an administrator.")
        return

    rec = (result.get("recommendation") or "").upper()
    st.markdown(f"### Recommendation: {recommendation_badge(rec)}")

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
