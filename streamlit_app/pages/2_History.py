import streamlit as st
from common import require_login, list_analyses, get_analysis_detail, render_result

st.set_page_config(page_title="History - FinGuardian AI", page_icon=":scroll:", layout="centered")
require_login()

st.title("Your Analysis History")

resp = list_analyses()
if resp.status_code != 200:
    st.error(f"Could not load history: {resp.text}")
    st.stop()

history = resp.json()
if not history:
    st.info("No analyses yet -- run one from the Analyze page.")
    st.stop()

pending = [h for h in history if h["status"] == "pending_review"]
if pending:
    st.warning(f"{len(pending)} case(s) awaiting your review.")

for entry in history:
    status_label = "[PENDING REVIEW]" if entry["status"] == "pending_review" else "[COMPLETED]"
    label = f"{status_label} {entry['symbol']} -- {entry['recommendation'] or entry['status']} -- {entry['created_at'][:16].replace('T', ' ')}"
    with st.expander(label):
        detail_resp = get_analysis_detail(entry["thread_id"])
        if detail_resp.status_code == 200:
            render_result(detail_resp.json())
        else:
            st.error("Could not load details for this analysis.")
