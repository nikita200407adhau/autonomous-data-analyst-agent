import operator
from typing import Annotated, Any, Optional, TypedDict

import pandas as pd
from langgraph.graph import END, START, StateGraph

from agent import (
    MAX_RETRIES, generate_action, get_schema, is_safe_python, is_safe_sql,
    llm, normalize, run_python,
)


# ------------------------------------------------------------------ STATE
class AgentState(TypedDict, total=False):
    question: str
    conn: Any                                  # SQLite connection
    schema: str
    action: Optional[dict]                     # {"tool", "reasoning", "code"}
    error: Optional[str]
    df: Any                                    # result table
    attempts: int
    summary: str
    steps: Annotated[list, operator.add]       # nodes ADD to this list, never overwrite


# ------------------------------------------------------------------ NODES
def inspect_node(state: AgentState) -> dict:
    schema = get_schema(state["conn"])
    return {
        "schema": schema,
        "attempts": 0,
        "error": None,
        "df": None,
        "steps": [("1. Inspect schema", schema)],
    }


def plan_node(state: AgentState) -> dict:
    """LLM chooses SQL or Python. If the last try failed, it sees the error and fixes it."""
    attempts = state["attempts"] + 1
    prev = state.get("action")
    try:
        action = generate_action(
            state["question"], state["schema"],
            state.get("error") if prev else None, prev,
        )
    except Exception as e:
        msg = f"Model returned invalid output: {e}"
        return {"attempts": attempts, "action": None, "error": msg,
                "steps": [(f"2. Attempt {attempts}: planning failed", msg)]}
    title = f"2. Attempt {attempts}: choose tool = {action['tool'].upper()}"
    return {"attempts": attempts, "action": action, "error": None,
            "steps": [(title, f"{action['reasoning']}\n\n{action['code']}")]}


def execute_node(state: AgentState) -> dict:
    action = state.get("action")
    if action is None:                         # planning failed, nothing to run
        return {}
    tool, code = action["tool"], action["code"]
    try:
        if tool == "python":
            ok, why = is_safe_python(code)
            if not ok:
                raise PermissionError("Blocked by guardrail: " + why)
            df = run_python(code, state["conn"])
        else:
            if not is_safe_sql(code):
                raise PermissionError("Blocked by guardrail: only a single SELECT is allowed.")
            df = normalize(pd.read_sql(code, state["conn"]))
        return {"df": df, "error": None,
                "steps": [("3. Execute", f"{len(df)} rows returned")]}
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        return {"df": None, "error": err,
                "steps": [("Error -> reflect and retry", err)]}


def summarize_node(state: AgentState) -> dict:
    df = state["df"]
    text = llm(
        f"Question: {state['question']}\nResult (first 30 rows):\n{df.head(30).to_string(index=False)}\n\n"
        "Write a short executive summary: 2-3 key insights and 1 recommendation. Be specific with numbers."
    )
    return {"summary": text, "steps": [("4. Summarize", "Insights generated")]}


def give_up_node(state: AgentState) -> dict:
    return {"summary": "I could not produce a valid answer for this question.",
            "steps": [("Stopped", f"Gave up after {state['attempts']} attempts")]}

# ------------------------------------------------------------------ EDGES
def route_after_execute(state: AgentState) -> str:
    """Decide what happens after the code runs."""
    if state.get("df") is not None and state.get("error") is None:
        return "summarize"            # success
    if state["attempts"] >= MAX_RETRIES:
        return "give_up"              # too many failures
    return "plan"                     # reflect and try again


builder = StateGraph(AgentState)
builder.add_node("inspect", inspect_node)
builder.add_node("plan", plan_node)
builder.add_node("execute", execute_node)
builder.add_node("summarize", summarize_node)
builder.add_node("give_up", give_up_node)

builder.add_edge(START, "inspect")
builder.add_edge("inspect", "plan")
builder.add_edge("plan", "execute")
builder.add_conditional_edges(
    "execute",
    route_after_execute,
    {"summarize": "summarize", "plan": "plan", "give_up": "give_up"},
)
builder.add_edge("summarize", END)
builder.add_edge("give_up", END)

graph = builder.compile()


def run_graph_agent(question: str, conn) -> dict:
    """Same output shape as run_agent() in agent.py, so app.py barely changes."""
    final = graph.invoke({"question": question, "conn": conn, "steps": []})
    action = final.get("action") or {}
    return {
        "steps": final["steps"],
        "df": final.get("df"),
        "tool": action.get("tool") if final.get("df") is not None else None,
        "code": action.get("code", ""),
        "summary": final["summary"],
    }