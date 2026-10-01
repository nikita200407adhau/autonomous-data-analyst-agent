import ast, builtins, json, os, re, sqlite3, time
import numpy as np
import pandas as pd
from google import genai
from google.genai import types

MODEL = "gemini-3.8-flash"
MAX_RETRIES = 3
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|pragma|truncate)\b", re.I
)

# ---------------------------------------------------------------- LLM helpers
_models_cache = []


def get_models():
    """Ask Google which flash models this API key can use."""
    if not _models_cache:
        skip = ("image", "tts", "live", "audio", "embedding", "robotics", "computer")
        for m in client.models.list():
            n = m.name.replace("models/", "")
            if "flash" in n and not any(s in n for s in skip):
                if "generateContent" in (m.supported_actions or []):
                    _models_cache.append(n)
    return _models_cache


def llm(prompt: str, json_mode: bool = False) -> str:
    cfg = types.GenerateContentConfig(
        response_mime_type="application/json" if json_mode else "text/plain",
        temperature=0.1,
    )
    try:
        candidates = [MODEL] + [m for m in get_models() if m != MODEL]
    except Exception:
        candidates = [MODEL]

    last_err = None
    for model in candidates:
        for attempt in range(2):
            try:
                return client.models.generate_content(
                    model=model, contents=prompt, config=cfg
                ).text
            except Exception as e:
                last_err = e
                msg = str(e)
                if "503" in msg or "429" in msg or "UNAVAILABLE" in msg:
                    time.sleep(2)
                    continue  # retry same model once, then move on
                if "404" in msg:
                    break  # model not available, try next one
                raise
    raise last_err


# ---------------------------------------------------------------- data helpers
def load_csv(df: pd.DataFrame, table: str = "data") -> sqlite3.Connection:
    df = df.copy()
    df.columns = [re.sub(r"\W+", "_", c.strip()).strip("_") for c in df.columns]
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    df.to_sql(table, conn, index=False, if_exists="replace")
    return conn


def get_schema(conn, table: str = "data") -> str:
    cols = pd.read_sql(f"PRAGMA table_info({table})", conn)
    sample = pd.read_sql(f"SELECT * FROM {table} LIMIT 3", conn)
    col_str = ", ".join(f"{r['name']} ({r['type']})" for _, r in cols.iterrows())
    return f"Table `{table}` columns: {col_str}\nSample rows:\n{sample.to_string(index=False)}"


def normalize(res) -> pd.DataFrame:
    """Turn any result (DataFrame, Series, single value) into a clean DataFrame."""
    if isinstance(res, pd.Series):
        res = res.to_frame().reset_index()
    elif not isinstance(res, pd.DataFrame):
        res = pd.DataFrame({"value": [res]})
    res = res.copy()
    res.columns = [str(c) for c in res.columns]
    for c in res.columns:
        if str(res[c].dtype).startswith("period") or pd.api.types.is_datetime64_any_dtype(res[c]):
            res[c] = res[c].astype(str)
    return res


# ---------------------------------------------------------------- guardrails
def is_safe_sql(sql: str) -> bool:
    """Single read-only SELECT/WITH statement only."""
    s = sql.strip().rstrip(";")
    return (
        s.lower().startswith(("select", "with"))
        and ";" not in s
        and not FORBIDDEN_SQL.search(s)
    )


BLOCKED_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "input", "globals", "locals",
    "vars", "getattr", "setattr", "delattr", "os", "sys", "subprocess", "builtins",
}
BLOCKED_ATTRS = {
    "to_csv", "to_excel", "to_pickle", "to_sql", "to_parquet", "to_feather", "to_hdf",
    "to_json", "to_html", "to_latex", "to_markdown", "to_clipboard", "to_xml",
    "to_orc", "to_stata", "eval",
}
SAFE_BUILTINS = {
    n: getattr(builtins, n)
    for n in ["len", "range", "min", "max", "sum", "abs", "round", "sorted", "list",
              "dict", "set", "tuple", "str", "int", "float", "bool", "enumerate",
              "zip", "isinstance", "any", "all", "map", "filter", "reversed", "pow", "divmod"]
}


def is_safe_python(code: str):
    """Basic static check: no imports, no file/system access, no private attributes.
    This is a guardrail, not a full sandbox. Do not expose the app to untrusted users."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return False, "Imports are not allowed (df, pd and np are already available)."
        if isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            return False, f"`{node.id}` is not allowed."
        if isinstance(node, ast.Attribute) and (
            node.attr.startswith("_") or node.attr.startswith("read_") or node.attr in BLOCKED_ATTRS
        ):
            return False, f"`.{node.attr}` is not allowed."
    return True, ""


def run_python(code: str, conn) -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM data", conn)
    env = {"__builtins__": SAFE_BUILTINS, "pd": pd, "np": np, "df": df}
    exec(code, env)
    if "result" not in env:
        raise ValueError("Your code must assign the final answer to a variable named `result`.")
    return normalize(env["result"])


# ---------------------------------------------------------------- the agent
def generate_action(question, schema, error=None, prev=None) -> dict:
    prompt = f"""You are a senior data analyst with two tools.

TOOL "sql": one read-only SQLite SELECT. Use it for filtering, grouping, ranking, totals and simple trends.
TOOL "python": pandas code. Use it for correlations, growth rates, percent of total, outliers,
rolling averages, or anything awkward in SQL.
  - DataFrame `df` holds the full table. `pd` and `np` are available. Do not use imports.
  - Assign the final answer (DataFrame, Series or single value) to a variable named `result`.
  - Date columns are stored as text: check the sample rows for the format, then use
    pd.to_datetime(..., errors="coerce").

{schema}

Question: {question}
"""
    if error:
        prompt += (
            f"\nYour previous attempt (tool={prev['tool']}):\n{prev['code']}\n"
            f"failed with: {error}\nFix it. You may switch tools.\n"
        )
    prompt += (
        '\nPrefer sql when it is enough. Return JSON only: '
        '{"tool": "sql" or "python", "reasoning": "<one sentence>", "code": "<code>"}'
    )
    out = json.loads(llm(prompt, json_mode=True))
    return {
        "tool": str(out.get("tool", "sql")).lower().strip(),
        "reasoning": out.get("reasoning", ""),
        "code": str(out.get("code", "")).strip(),
    }


def run_agent(question: str, conn) -> dict:
    steps, df, prev, err = [], None, None, None
    schema = get_schema(conn)
    steps.append(("1. Inspect schema", schema))

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            action = generate_action(question, schema, err, prev)
        except Exception as e:
            err = f"Model returned invalid output: {e}"
            steps.append(("Error -> retry", err))
            continue
        prev = action
        tool, code = action["tool"], action["code"]
        steps.append((
            f"2. Attempt {attempt}: choose tool = {tool.upper()}",
            f"{action['reasoning']}\n\n{code}",
        ))
        try:
            if tool == "python":
                ok, why = is_safe_python(code)
                if not ok:
                    raise PermissionError("Blocked by guardrail: " + why)
                df = run_python(code, conn)
            else:
                if not is_safe_sql(code):
                    raise PermissionError("Blocked by guardrail: only a single SELECT is allowed.")
                df = normalize(pd.read_sql(code, conn))
            steps.append(("3. Execute", f"{len(df)} rows returned"))
            break
        except Exception as e:
            df = None
            err = f"{type(e).__name__}: {e}"
            steps.append(("Error -> self-correct", err))

    if df is None:
        return {"steps": steps, "df": None, "tool": None, "code": prev["code"] if prev else "",
                "summary": "I could not produce a valid answer for this question."}

    summary = llm(
        f"Question: {question}\nResult (first 30 rows):\n{df.head(30).to_string(index=False)}\n\n"
        "Write a short executive summary: 2-3 key insights and 1 recommendation. Be specific with numbers."
    )
    steps.append(("4. Summarize", "Insights generated"))
    return {"steps": steps, "df": df, "tool": prev["tool"], "code": prev["code"], "summary": summary}
