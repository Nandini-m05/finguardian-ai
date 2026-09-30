import streamlit as st
from common import init_session_state, login, register, logout, list_analyses

st.set_page_config(page_title="FinGuardian AI", page_icon=":chart_with_upwards_trend:", layout="centered")
init_session_state()

st.title("FinGuardian AI")
st.caption("Multi-agent financial intelligence -- market data, news sentiment, fraud detection, and human-reviewed recommendations, in one pipeline.")

if not st.session_state.token:
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
                    st.success("Account created -- you can log in now.")
                else:
                    st.error(error)

else:
    col1, col2 = st.columns([4, 1])
    col1.write(f"Logged in as **{st.session_state.email}**")
    if col2.button("Log out"):
        logout()
        st.rerun()

    st.write("---")
    st.subheader("Your activity")

    resp = list_analyses()
    if resp.status_code == 200:
        history = resp.json()
        total = len(history)
        flagged = sum(1 for h in history if h.get("requires_human_review"))
        scored = [h["risk_score"] for h in history if h.get("risk_score") is not None]
        avg_risk = round(sum(scored) / len(scored), 1) if scored else "N/A"

        c1, c2, c3 = st.columns(3)
        c1.metric("Analyses run", total)
        c2.metric("Flagged for review", flagged)
        c3.metric("Average risk score", avg_risk)
    else:
        st.info("Run your first analysis to see your activity here.")

    st.write("---")
    st.write("Use the sidebar to open **Analyze**, **History**, or **How It Works**.")
