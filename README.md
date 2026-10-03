# Autonomous Data Analyst Agent
Natural-language questions -> SQL -> execution -> self-correction -> charts + executive summary.

## Run
    pip install -r requirements.txt
    export GEMINI_API_KEY="your_key"      # Windows: set GEMINI_API_KEY=your_key
    streamlit run app.py

## Roadmap
- [x] Week 1: CSV -> SQLite, SQL generation, read-only guardrail, retry loop
- [ ] Week 2: Python/Pandas tool, smarter charts, PDF/Excel export
- [ ] Week 3: Migrate to LangGraph (plan -> act -> observe -> reflect)
- [ ] Week 4: 20-question benchmark, README diagram, demo GIF, deploy

## Architecture

```mermaid
flowchart TD
    A([Start]) --> B[Inspect schema]
    B --> C[Plan: Gemini picks SQL or Python]
    C --> D[Execute with guardrails]
    D -->|success| E[Summarize insights]
    D -->|error, tries left| C
    D -->|3 failures| F[Give up]
    E --> G([End])
    F --> G
```
