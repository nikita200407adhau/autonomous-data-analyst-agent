"""Find out which Gemini models work for your key, and how fast they are.

Usage (key must be set):
    python check_gemini.py

It sends one tiny request to up to 6 flash models and prints the time or the error for each.
Put the fastest working model into the GEMINI_MODEL setting.
"""
import os
import time

from google import genai
from google.genai import types

key = os.getenv("GEMINI_API_KEY")
if not key:
    raise SystemExit("Set GEMINI_API_KEY first.")

client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=60_000))
skip = ("image", "tts", "live", "audio", "embedding", "robotics", "computer")
names = [
    m.name.replace("models/", "")
    for m in client.models.list()
    if "flash" in m.name and "generateContent" in (m.supported_actions or []) and not any(s in m.name for s in skip)
]
print("Flash models on this key:", ", ".join(names) or "none found")

results = []
for name in names[:6]:
    start = time.time()
    try:
        client.models.generate_content(model=name, contents="Reply with the single word OK")
        secs = time.time() - start
        results.append((secs, name))
        print(f"  OK      {secs:5.1f}s  {name}")
    except Exception as e:
        print(f"  FAILED  {time.time() - start:5.1f}s  {name}  ->  {str(e)[:90]}")

if results:
    results.sort()
    print(f"\nFastest working model: {results[0][1]}")
    print(f'Windows PowerShell:  $env:GEMINI_MODEL="{results[0][1]}"')
    print("Streamlit Cloud:     add  GEMINI_MODEL = \"" + results[0][1] + "\"  to Secrets")
else:
    print("\nNo model answered. Check your quota in AI Studio, or try again in a few minutes.")