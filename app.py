import pandas as pd
import plotly.express as px
import streamlit as st
from agent import load_csv, run_agent

st.set_page_config(page_title="Autonomous Data Analyst Agent", layout="wide")


def show_df(d):
    # Plain HTML table: avoids pyarrow, which Windows is blocking
    html = d.head(200).to_html(index=False)
    st.markdown(f'<div style="overflow-x:auto">{html}</div>', unsafe_allow_html=True)


st.title("Autonomous Data Analyst Agent")
st.caption("Ask a business question in plain English. The agent writes SQL, runs it, fixes its own errors, and explains the result.")

file = st.file_uploader("Upload a CSV", type="csv")
if file:
    df = pd.read_csv(file, encoding_errors="ignore")
    conn = load_csv(df)
    show_df(df.head())

    q = st.text_input("Your question", placeholder="Which region had the highest profit?")
    if st.button("Analyze") and q:
        with st.spinner("Agent is working..."):
            res = run_agent(q, conn)

        with st.expander("Agent steps", expanded=True):
            for title, detail in res["steps"]:
                st.markdown(f"**{title}**")
                st.code(detail)

        if res["df"] is not None:
            out = res["df"]
            st.subheader("Result")
            show_df(out)
            num = out.select_dtypes("number").columns
            if len(out.columns) >= 2 and len(num) >= 1 and 1 < len(out) <= 50:
                x = [c for c in out.columns if c not in num][:1] or [out.columns[0]]
                try:
                    st.plotly_chart(px.bar(out, x=x[0], y=num[0]), use_container_width=True)
                except Exception as e:
                    st.info(f"Chart unavailable on this machine: {e}")
        st.subheader("Insights")
        st.write(res["summary"])