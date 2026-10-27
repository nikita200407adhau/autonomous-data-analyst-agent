import io
import os
import re
import time

import pandas as pd
import plotly.express as px
import streamlit as st

import agent as agent_mod
import answer_cache
from agent import load_csv
from graph_agent import run_graph_agent
from style import (PALETTE, footer, hero, inject_css, ledger, note, section,
                   style_fig, table, worksheet)

st.set_page_config(page_title="Autonomous Data Analyst Agent", page_icon="📊", layout="wide")
inject_css()
hero()


def pick_chart(out):
    """Line chart for a time-like x axis, bar chart otherwise."""
    num = out.select_dtypes("number").columns.tolist()
    cat = [c for c in out.columns if c not in num]
    if not num or not (2 <= len(out) <= 60):
        return None
    x = cat[0] if cat else out.columns[0]
    ys = [c for c in num if c != x][:3]
    if not ys:
        return None
    y = ys if len(ys) > 1 else ys[0]
    if re.search(r"date|month|year|day|week|quarter|period", x, re.I):
        fig = px.line(out, x=x, y=y, markers=True, color_discrete_sequence=PALETTE)
    else:
        fig = px.bar(out, x=x, y=y, color_discrete_sequence=PALETTE)
    return style_fig(fig)


@st.cache_resource(show_spinner=False)
def get_data(raw: bytes):
    """Read the CSV and build the SQLite table once, not on every click."""
    df = pd.read_csv(io.BytesIO(raw), encoding_errors="ignore")
    return df, load_csv(df), answer_cache.data_key(df)


section("Your data")
file = st.file_uploader("Upload a CSV file", type="csv")
use_sample = st.checkbox("Use the sample Superstore data instead")
source = file if file else ("sample_data.csv" if use_sample else None)

if source is None:
    note("Upload a CSV file, or tick the sample data box, to get started.")
elif isinstance(source, str) and not os.path.exists(source):
    note("sample_data.csv was not found in the project folder. Add it, or upload your own CSV.", bad=True)
else:
    if hasattr(source, "getvalue"):
        raw = source.getvalue()
    else:
        with open(source, "rb") as fh:
            raw = fh.read()
    df, conn, dkey = get_data(raw)
    use_cache = isinstance(source, str)   # saved answers are only used for the built-in sample data
    table(df.head())

    section("Your question")
    q_in = st.text_input("Ask a question about this data", placeholder="Which region has the highest sales?",
                         label_visibility="collapsed", key="q")
    go = st.button("Analyze data")

    clicked = None
    examples = answer_cache.questions(dkey) if use_cache else []
    if examples:
        st.caption("Saved examples. These open instantly and use no AI call:")
        with st.container(key="examples"):
            cols = st.columns(3)
            for i, qq in enumerate(examples[:6]):
                if cols[i % 3].button(qq, key=f"ex{i}"):
                    clicked = qq

    question = clicked or (q_in if go and q_in else None)
    if question:
        res = answer_cache.get(dkey, question) if use_cache else None
        from_cache = res is not None
        t0 = time.time()
        n0 = len(agent_mod.LLM_LOG)
        if not from_cache:
            with st.spinner("The agent is writing and running code..."):
                res = run_graph_agent(question, conn)
            if use_cache:
                answer_cache.put(dkey, question, res)
        secs = time.time() - t0
        out = res["df"]
        calls = agent_mod.LLM_LOG[n0:]

        no_key = any("GEMINI_API_KEY" in str(d) for _, d in res["steps"])
        quota_hit = any(("429" in str(d) or "RESOURCE_EXHAUSTED" in str(d)) for _, d in res["steps"])
        if out is None and no_key:
            note("No Gemini API key was found, so the agent cannot call the AI. Set GEMINI_API_KEY and restart "
                 "the app. Saved examples still work.", bad=True)
        elif out is None and any(k in str(d) for _, d in res["steps"] for k in ("504", "DEADLINE", "503", "UNAVAILABLE")) and not quota_hit:
            note("Google's AI service was too slow or busy for this request. Wait a minute and try again, "
                 "or switch to a faster model (see check_gemini.py).", bad=True)
        elif out is None and quota_hit:
            note("The free AI quota for this demo is used up for now. Try one of the saved examples, "
                 "try again later, or run the app with your own Gemini key.", bad=True)
        elif out is None:
            note("The agent could not answer this one. Try rephrasing, or name the column you mean.", bad=True)
        else:
            retries = sum(1 for title, _ in res["steps"] if title.startswith("Error"))
            ledger([("Tool used", res["tool"].upper()), ("Rows", f"{len(out):,}"),
                    ("Retries", retries), ("Time", "saved" if from_cache else f"{secs:.1f}s")])
            if from_cache:
                st.caption("This is a saved answer from an earlier run of the same question. No AI call was made.")
            elif calls:
                failed = sum(1 for c in calls if not c["ok"])
                slow = max(calls, key=lambda c: c["seconds"])
                st.caption(f"The agent made {len(calls)} model calls ({failed} failed or busy). "
                           f"Slowest: {slow['seconds']:.1f}s on {slow['model']}.")

            section("Result")
            table(out, round_floats=True)
            st.download_button("Download as CSV", out.to_csv(index=False).encode("utf-8"),
                               file_name="result.csv", mime="text/csv")
            try:
                fig = pick_chart(out)
                if fig is not None:
                    try:
                        st.plotly_chart(fig, width="stretch")
                    except TypeError:  # older Streamlit versions
                        st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                note(f"The chart could not be drawn: {e}")

            section("Insights")
            with st.container(key="insights"):
                st.write(res["summary"].replace("$", "\\$"))

        section("How the agent got there")
        worksheet(res["steps"])

footer()