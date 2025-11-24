# Agentic Research Collaborator (Backend)

FastAPI-based orchestration layer for a multi-agent research assistant.

## Features
- Python 3.10+
- Agents: Reader → Critic → Synthesizer → Verifier
- Endpoints:
  - `POST /run` → `{ run_id }`
  - `GET /trace/{run_id}` → full conversation trace
  - `GET /insight/{run_id}` → final InsightReport
- Traces saved under `data/runs/<run_id>/`
- Mock Grok API call (no external dependency)

## Environment
- `LLM_PROVIDER` = `groq` or `grok` (auto if omitted based on which key you set)
- `GROQ_API_KEY` for Groq, or `GROK_API_KEY` for xAI Grok
- `MODEL_NAME` (Groq ex: `llama-3.3-70b-versatile`; Grok ex: `grok`)
- `PORT` (default: `8080`)
- Optional: `ENABLE_BM25=auto|true|false` (default `auto`), `BM25_FILES_DIR` (default `files`)

## Quickstart (Windows PowerShell)

```powershell
# Create and activate a virtual environment (recommended)
python -m venv .venv
. .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure Groq (recommended)
$env:LLM_PROVIDER = "groq"
$env:GROQ_API_KEY = "<your_groq_key>"
$env:MODEL_NAME   = "llama-3.3-70b-versatile"

# Optional BM25 (add PDFs in .\files first)
$env:ENABLE_BM25 = "auto"

# Run API server
$env:PORT=8080
uvicorn api.server:app --host 0.0.0.0 --port $env:PORT
```

## Example: Mock Run (no UI)

```powershell
python examples/mock_run.py
```

It will print a `run_id` and write artifacts to `data/runs/<run_id>/trace.json` and `report.json`.

## Try the system end-to-end (Groq)

1) Start the server as above.
2) In a new PowerShell window:

```powershell
$run = Invoke-RestMethod -Method Post -Uri http://localhost:8080/run -ContentType "application/json" -Body '{"topic":"Impact of RLHF on code LLMs","max_turns":2,"consensus_threshold":0.8}'
$run
Invoke-RestMethod -Method Get -Uri ("http://localhost:8080/trace/" + $run.run_id)
Invoke-RestMethod -Method Get -Uri ("http://localhost:8080/insight/" + $run.run_id)
```

## LangGraph + BM25 example (Groq)

```powershell
# Requires PDFs under .\files and GROQ_API_KEY set as above
python examples/langgraph_bm25.py
```

## Project Layout
```
/api/server.py               # FastAPI app + routes
/agents/base_agent.py        # abstract agent + mock Grok client
/agents/roles/reader.py      # extracts key methods & findings
/agents/roles/critic.py      # finds contradictions & missing evidence
/agents/roles/synthesizer.py # merges insights into hypotheses
/agents/roles/verifier.py    # re-checks claims via retriever
/orchestrator/graph.py       # coordinates message flow among agents
/schemas/models.py           # Pydantic schemas: Message, Turn, Trace, InsightReport
/data/runs/                  # persisted traces & reports
```

## Notes
- The mock API returns deterministic content, citations, and confidence values.
- Real Grok integration can replace `BaseAgent._call_grok_api` keeping the same return contract.
