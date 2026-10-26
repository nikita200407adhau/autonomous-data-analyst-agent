"""Saved answers for the sample dataset.

Every successful answer on the sample data is stored in answer_cache.json. Asking the same question
again (or clicking a saved example) shows the stored answer with no AI call, so repeat tests and
live demos do not use up the free API quota.
"""
import hashlib
import json
import os

import pandas as pd

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "answer_cache.json")


def data_key(df: pd.DataFrame) -> str:
    """Fingerprint of the table contents (same on Windows and Linux)."""
    text = df.to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _qkey(question: str) -> str:
    return " ".join(question.lower().split())


def _load() -> dict:
    try:
        with open(PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get(dkey: str, question: str):
    entry = _load().get(dkey, {}).get(_qkey(question))
    if not entry:
        return None
    res = dict(entry)
    res["df"] = pd.DataFrame(entry["df"]["data"], columns=entry["df"]["columns"])
    res["steps"] = [tuple(s) for s in entry["steps"]]
    return res


def put(dkey: str, question: str, res: dict) -> None:
    if res.get("df") is None:
        return
    data = _load()
    data.setdefault(dkey, {})[_qkey(question)] = {
        "question": question.strip(),
        "steps": [list(s) for s in res["steps"]],
        "df": {
            "columns": [str(c) for c in res["df"].columns],
            "data": json.loads(res["df"].to_json(orient="values", date_format="iso")),
        },
        "tool": res["tool"],
        "code": res["code"],
        "summary": res["summary"],
    }
    try:
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, ensure_ascii=False)
    except OSError:
        pass  # read-only folder: the app still works, it just cannot save


def questions(dkey: str) -> list:
    return [e["question"] for e in _load().get(dkey, {}).values()]