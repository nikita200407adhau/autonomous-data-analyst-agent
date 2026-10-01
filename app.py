import re
import pandas as pd
import plotly.express as px
import streamlit as st
from agent import load_csv, run_agent

st.set_page_config(page_title="Autonomous Data Analyst Agent", layout="wide")


def show_df(d):
    # Plain HTML table: avoids pyarrow, which Windows is blocking
    html = d.head(200).to_html(index=False)
    st.markdown(f'<div style="overflow-x:auto">{html}</div>', unsafe_allow_html=True)


def pick_chart(out):
    """Line chart for time-like x axis, bar chart otherwise."""
    num = out.select_dtypes("number").columns.tolist()
    cat = [c for c in out.columns if c not in num]
    if not num or not (2 <= len(out) <= 60):
        return None
    x = cat[0] if cat else out.columns[0]
    ys = [c for c in num if c != x][:3]
    if not ys:
        return None
    if re.search(r"date|month|year|day|week|quarter|period", x, re.I):
        return px.line(out, x=x, y=ys, markers=True)
    return px.bar(out, x=x, y=ys, barmode="group")


st.title("Autonomous Data Analyst Agent")
st.caption("Ask a business question in plain English. The agent picks SQL or Python, runs it, fixes its own errors, and explains the result.")

file = st.file_uploader("Upload a CSV", type="csv")
if file:
    df = pd.read_csv(file, encoding_errors="ignore")
    conn = load_csv(df)
    show_df(df.head())

    q = st.text_input("Your question", placeholder="Is there a correlation between discount and profit?")
    if st.button("Analyze") and q:
        with st.spinner("Agent is working..."):
            res = run_agent(q, conn)

        with st.expander("Agent steps", expanded=True):
            for title, detail in res["steps"]:
                st.markdown(f"**{title}**")
                st.code(detail)

        if res["df"] is not None:
            out = res["df"]
            st.caption(f"Tool used: {res['tool'].upper()}")
            st.subheader("Result")
            show_df(out)
            st.download_button("Download result as CSV", out.to_csv(index=False).encode("utf-8"),
                        file_name="result.csv", mime="text/csv")
            try:
                fig = pick_chart(out)
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.info(f"Chart unavailable on this machine: {e}")
        st.subheader("Insights")
        st.write(res["summary"])
