import streamlit as st
from common import require_login, run_analysis, render_result

st.set_page_config(page_title="Analyze - FinGuardian AI", page_icon=":bar_chart:", layout="centered")
require_login()

st.title("Analyze a Symbol")
st.write(f"Logged in as **{st.session_state.email}**")
st.write("---")

symbol = st.text_input("Stock symbol", value="AAPL", max_chars=10).upper().strip()
st.caption("Each analysis uses a real, limited external API call (25/day) -- avoid re-running the same symbol unnecessarily.")

if st.button("Analyze", type="primary", disabled=not symbol):
    with st.spinner(f"Running the 8-agent pipeline for {symbol}... this can take 10-20 seconds."):
        resp = run_analysis(symbol)

    if resp.status_code == 200:
        render_result(resp.json())
    elif resp.status_code == 429:
        st.error("Rate limit reached (5 analyses/minute). Please wait a moment and try again.")
    elif resp.status_code in (401, 403):
        st.error("Session expired -- please log out and log back in from the Home page.")
    else:
        st.error(f"Request failed ({resp.status_code}): {resp.text}")
