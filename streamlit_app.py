"""Streamlit interface. Run: python -m streamlit run streamlit_app.py."""

import hmac
import json
import os
from datetime import datetime, timezone

import streamlit as st


st.set_page_config(page_title="Post Studio | LinkedIn Content Manager", page_icon="✦", layout="wide")

# Access secrets before loading the pipeline; Streamlit exposes root secrets
# as environment variables. Local development can continue using .env.
st.secrets.load_if_toml_exists()

from pipeline import STAGES, run_pipeline, validate_configuration


def require_access():
    password = os.getenv("APP_PASSWORD", "")
    if not password or st.session_state.get("authenticated"):
        return
    st.title("Post Studio")
    st.caption("Enter your access password to open the content workspace.")
    with st.form("access"):
        entered = st.text_input("Access password", type="password")
        submitted = st.form_submit_button("Open workspace")
    if submitted:
        if hmac.compare_digest(entered.encode(), password.encode()):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()


require_access()

st.markdown("""
<style>
.block-container {max-width: 1180px; padding-top: 2.7rem;}
h1 {letter-spacing: -0.04em;}
div[data-testid="stMetric"] {background: #f1f5f9; border-radius: 12px; padding: 16px;}
div[data-testid="stForm"] {border-radius: 16px;}
.studio-eyebrow {color: #2563eb; font-size: .8rem; letter-spacing: .16em; font-weight: 700;}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ✦ Post Studio")
    st.caption("Your LinkedIn writing workspace")
    st.divider()
    st.markdown("**From idea to publishing brief**")
    for index, title in enumerate(STAGES, 1):
        st.write(f"{index:02d} · {title}")
    st.divider()
    st.caption("Free-tier limits can pause generation. Keep this tab open while it runs.")
    st.caption("Posts are prepared for review. Publishing to LinkedIn is manual.")

st.markdown('<div class="studio-eyebrow">RESEARCH · WRITE · REFINE</div>', unsafe_allow_html=True)
st.title("A better LinkedIn post starts here.")
st.write("Turn a topic into a researched draft, an improved post, and a plan for publishing it.")

left, right = st.columns([2, 1])
with left:
    with st.form("topic_form"):
        topic = st.text_area("What would you like to write about?", max_chars=200,
                             placeholder="e.g. Python automation tips for beginners", height=110)
        st.caption("Be specific about the topic and audience. Use 3–200 characters.")
        submitted = st.form_submit_button("Generate content", type="primary", use_container_width=True)
with right:
    st.markdown("#### A few starting points")
    st.markdown("- Practical AI for small businesses\n- Lessons from your first Python project\n- Making remote teamwork easier")

configuration_error = None
try:
    validate_configuration()
except ValueError as exc:
    configuration_error = str(exc)
    st.warning("API configuration is incomplete. Add your Groq and Serper keys before generating.")
    with st.expander("Setup instructions"):
        st.write(configuration_error)
        st.code('LLM_PROVIDER = "groq"\nGROQ_API_KEY = "your_groq_api_key"\nLLM_MODEL = "qwen/qwen3.8-27b"\nSERPER_API_KEY = "your_serper_api_key"', language="toml")
        st.caption("Locally, use .env. On Streamlit Community Cloud, use app Settings → Secrets.")

if submitted:
    if not 3 <= len(topic.strip()) <= 200:
        st.error("Enter a topic between 3 and 200 characters.")
    elif configuration_error:
        st.error("Finish API configuration before generating.")
    else:
        st.session_state.report = {"topic": topic.strip(), "stages": {}, "complete": False,
                                   "created_at": datetime.now(timezone.utc).isoformat()}
        progress = st.progress(0)
        with st.status("Researching your topic…", expanded=True) as status:
            st.write("Generation can take several minutes, including free-tier waiting periods.")

            def stage_finished(index, title, text):
                st.session_state.report["stages"][title] = text
                progress.progress((index + 1) / len(STAGES))
                st.write(f"✓ {title} complete")
                if index + 1 < len(STAGES):
                    status.update(label=f"Working on: {STAGES[index + 1]}")

            try:
                outputs = run_pipeline(topic, on_stage=stage_finished)
                st.session_state.report["stages"] = outputs
                st.session_state.report["complete"] = True
                status.update(label="Your content is ready", state="complete", expanded=False)
            except Exception:
                # Provider exceptions may include account identifiers; keep the
                # public UI generic and retain any successfully completed stages.
                status.update(label="Generation could not finish", state="error")
                st.error("The service could not finish this run. Check your API keys and limits, then try again. Any completed stages are available below.")

report = st.session_state.get("report")
if report and report["stages"]:
    st.divider()
    st.subheader("Your content" if report["complete"] else "Partial results")
    st.caption(report["topic"])
    stages = report["stages"]
    if "Optimized post" in stages:
        st.markdown("#### Post to review")
        stages["Optimized post"] = st.text_area(
            "Copy and edit your optimized post", stages["Optimized post"], height=300,
            key="post_" + report["created_at"])
    tabs = st.tabs(list(stages))
    for tab, (title, text) in zip(tabs, stages.items()):
        with tab:
            st.markdown(text)
    plain_text = report["topic"] + "\n\n" + "\n\n".join(f"{title}\n{'-' * len(title)}\n{text}" for title, text in stages.items())
    text_col, json_col = st.columns(2)
    with text_col:
        st.download_button("Download report (.txt)", plain_text, file_name="linkedin-content.txt", mime="text/plain", use_container_width=True)
    with json_col:
        st.download_button("Download report (.json)", json.dumps(report, ensure_ascii=False, indent=2), file_name="linkedin-content.json", mime="application/json", use_container_width=True)
else:
    st.divider()
    st.markdown("#### One topic. Five perspectives.")
    st.caption("Your research, draft, critique, optimized post, and publishing brief will appear here.")
