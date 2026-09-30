import streamlit as st
from common import require_login, list_pending_reviews, get_analysis_detail, render_result

st.set_page_config(page_title="Admin Review - FinGuardian AI", page_icon=":clipboard:", layout="centered")
require_login()

if st.session_state.get("role") != "admin":
    st.error("Admin access required. This page is only usable by accounts with the admin role.")
    st.stop()

st.title("Admin Review Queue")
st.write("Flagged cases from every other user, awaiting a decision. Your own submissions, if flagged, appear in your History page instead - separation of duties means you can't review your own case.")

resp = list_pending_reviews()
if resp.status_code != 200:
    st.error(f"Could not load review queue: {resp.text}")
    st.stop()

pending = resp.json()
if not pending:
    st.success("No cases currently awaiting review.")
    st.stop()

for entry in pending:
    label = f"{entry['symbol']} -- requested by {entry['requested_by_email']} -- {entry['created_at'][:16].replace('T', ' ')}"
    with st.expander(label, expanded=True):
        detail_resp = get_analysis_detail(entry["thread_id"])
        if detail_resp.status_code == 200:
            render_result(detail_resp.json(), allow_review=True)
        else:
            st.error("Could not load details for this case.")
