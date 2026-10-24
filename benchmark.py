"""Run every question in a CSV through the agent and save the results.

Usage:
    python benchmark.py "superstore sales.csv"
    python benchmark.py "superstore sales.csv" questions.csv
"""
import sys
import time

import pandas as pd

from agent import load_csv
from graph_agent import run_graph_agent

PAUSE_SECONDS = 3  # small pause between questions to avoid API rate limits


def compact(df, rows=6):
    """Short text version of a result table, easy to compare with Excel."""
    if df is None:
        return ""
    text = df.head(rows).to_string(index=False)
    more = f"\n... ({len(df)} rows total)" if len(df) > rows else ""
    return text + more


def main():
    data_path = sys.argv[1]
    q_path = sys.argv[2] if len(sys.argv) > 2 else "questions.csv"

    conn = load_csv(pd.read_csv(data_path, encoding_errors="ignore"))
    qs = pd.read_csv(q_path)
    qs = qs[qs["question"].notna()].reset_index(drop=True)

    records = []
    for i, row in qs.iterrows():
        q = row["question"]
        print(f"[{i + 1}/{len(qs)}] {q}")
        start = time.time()
        try:
            res = run_graph_agent(q, conn)
            retries = sum(1 for title, _ in res["steps"] if title.startswith("Error"))
            records.append({
                "question": q,
                "status": "answered" if res["df"] is not None else "no answer",
                "tool": res["tool"] or "",
                "retries": retries,
                "seconds": round(time.time() - start, 1),
                "agent_answer": compact(res["df"]),
                "code": res["code"],
                "summary": res["summary"],
            })
        except Exception as e:  # keep going even if one question crashes
            records.append({
                "question": q, "status": "crash", "tool": "", "retries": 0,
                "seconds": round(time.time() - start, 1),
                "agent_answer": "", "code": "", "summary": f"{type(e).__name__}: {e}",
            })
        time.sleep(PAUSE_SECONDS)

    out = pd.DataFrame(records)
    # bring in your correct answers so you can compare side by side
    if "correct_answer" in qs.columns:
        out.insert(1, "correct_answer", qs["correct_answer"].values[: len(out)])
    out["result"] = ""   # you fill in: correct / partial / wrong / error
    out["notes"] = ""
    out.to_csv("benchmark_results.csv", index=False)

    answered = (out["status"] == "answered").sum()
    print(f"\nDone. {answered}/{len(out)} questions answered. "
          f"Retries used: {out['retries'].sum()}. "
          f"Saved to benchmark_results.csv")


if __name__ == "__main__":
    main()
