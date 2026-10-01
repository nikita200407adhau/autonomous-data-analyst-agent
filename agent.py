import time
import os, re, json, sqlite3
import pandas as pd
from google import genai
from google.genai import types
MODEL = "gemini-3.8-flash"
MAX_RETRIES = 3
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|pragma|truncate)\b", re.I
)

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


def is_safe(sql: str) -> bool:
    """Guardrail: a single read-only SELECT/WITH statement only."""
    s = sql.strip().rstrip(";")
    return (
        s.lower().startswith(("select", "with"))
        and ";" not in s
        and not FORBIDDEN.search(s)
    )


def generate_sql(question, schema, error=None, prev_sql=None) -> dict:
    prompt = f"""You are a SQLite expert. Write ONE read-only SELECT query.
{schema}

Question: {question}
"""
    if error:
        prompt += f"\nYour previous query:\n{prev_sql}\nfailed with: {error}\nFix it.\n"
    prompt += '\nReturn JSON: {"reasoning": "<one sentence>", "sql": "<query>"}'
    return json.loads(llm(prompt, json_mode=True))


def run_agent(question: str, conn) -> dict:
    steps, df, sql, err = [], None, None, None
    schema = get_schema(conn)
    steps.append(("1. Inspect schema", schema))

    for attempt in range(1, MAX_RETRIES + 1):
        out = generate_sql(question, schema, err, sql)
        sql = out["sql"].strip()
        steps.append((f"2. Attempt {attempt}: write SQL", f"{out['reasoning']}\n\n{sql}"))

        if not is_safe(sql):
            err = "Blocked by guardrail: only a single SELECT is allowed."
            steps.append(("Guardrail", err))
            continue
        try:
            df = pd.read_sql(sql, conn)
            steps.append(("3. Execute", f"{len(df)} rows returned"))
            break
        except Exception as e:
            err = str(e)
            steps.append(("Error -> self-correct", err))

    if df is None:
        return {"steps": steps, "df": None, "sql": sql,
                "summary": "I could not produce a valid query for this question."}

    summary = llm(
        f"Question: {question}\nSQL result (first 30 rows):\n{df.head(30).to_string(index=False)}\n\n"
        "Write a short executive summary: 2-3 key insights and 1 recommendation. Be specific with numbers."
    )
    steps.append(("4. Summarize", "Insights generated"))
    return {"steps": steps, "df": df, "sql": sql, "summary": summary}
