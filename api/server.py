"""
FastAPI application for Agentic Research Collaborator.

Exposes:
- POST /run            -> Starts a run and returns { run_id }
- GET  /trace/{run_id} -> Returns the persisted trace
- GET  /insight/{run_id} -> Returns the final report

Environment variables:
- GROK_API_KEY: API key for future Grok integration (unused in mock)
- MODEL_NAME:   Model name to use (default: grok-beta)
- PORT:         Server port (default: 8080)
"""
from __future__ import annotations

import os
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path

# Optional: load environment from .env if present
try:  # pragma: no cover - optional dependency
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass
from fastapi.responses import HTMLResponse
from orchestrator.graph import Orchestrator
from schemas.models import InsightReport, RunRequest, RunResponse, Trace

app = FastAPI(title="Agentic Research Collaborator", version="0.1.0")

_orchestrator = Orchestrator()


@app.get("/")
def root() -> dict:
    """Landing route to help users discover available endpoints."""
    import os

    provider = os.getenv("LLM_PROVIDER") or (
        "gemini" if os.getenv("GEMINI_API_KEY") else (
            "groq" if os.getenv("GROQ_API_KEY") else (
                "grok" if os.getenv("GROK_API_KEY") else "mock"
            )
        )
    )
    model = os.getenv("MODEL_NAME", "")
    return {
        "app": "Agentic Research Collaborator",
        "status": "ok",
        "provider": provider,
        "model": model,
        "endpoints": {
            "POST /run": "Start a run with {topic, max_turns, consensus_threshold}",
            "GET /trace/{run_id}": "Fetch conversation trace",
            "GET /insight/{run_id}": "Fetch final insight report",
            "GET /graph/{run_id}": "View visual conversation flow graph for a specific run",
            "GET /graph": "View visual conversation flow graph for the most recent run",
            "GET /graph/animated/{run_id}": "🎬 View ANIMATED replay for a specific run",
            "GET /graph/animated": "🎬 View ANIMATED replay for the most recent run",
            "GET /graph/live/{run_id}": "View LIVE updating graph for a specific run",
            "GET /graph/live": "View LIVE updating graph for the most recent run",
            "GET /docs": "OpenAPI docs (interactive)",
            "GET /health": "Basic health check",
        },
        "note": "Root path '/' is informational only; use /run or /docs to interact.",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse)
def start_run(req: RunRequest) -> RunResponse:
    """Start an orchestration run for the given topic."""
    try:
        run_id = _orchestrator.run(
            topic=req.topic,
            max_turns=req.max_turns,
            consensus_threshold=req.consensus_threshold,
            enable_bm25=req.enable_bm25,
            files_dir=req.files_dir,
            bm25_k=req.bm25_k,
        )
        return RunResponse(run_id=run_id)
    except Exception as exc:
        # Surface provider rate-limit or transient errors as Service Unavailable
        raise HTTPException(status_code=503, detail=f"Run failed: {exc}")


@app.get("/trace/{run_id}", response_model=Trace)
def get_trace(run_id: Annotated[str, Path(min_length=3)]) -> Trace:
    """Retrieve the full trace for a run."""
    trace = _orchestrator.load_trace(run_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Run not found")
    return trace


@app.get("/insight/{run_id}", response_model=InsightReport)
def get_insight(run_id: Annotated[str, Path(min_length=3)]) -> InsightReport:
    """Retrieve the final report for a run."""
    report = _orchestrator.load_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail="Run not found")
    return report


# Graph endpoints - ORDER MATTERS! Specific routes must come before parameterized routes
@app.get("/graph/animated", response_class=HTMLResponse)
def get_latest_animated_graph():
    """Get an ANIMATED graph page for the most recent run."""
    from pathlib import Path
    from fastapi.responses import RedirectResponse
    
    # Find the most recent run directory
    runs_dir = Path(__file__).resolve().parent.parent / "data" / "runs"
    if not runs_dir.exists():
        raise HTTPException(status_code=404, detail="No runs found")
    
    run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
    if not run_dirs:
        raise HTTPException(status_code=404, detail="No runs found")
    
    latest_run_dir = max(run_dirs, key=lambda d: d.stat().st_mtime)
    run_id = latest_run_dir.name
    
    # Redirect to the animated graph for this run
    return RedirectResponse(url=f"/graph/animated/{run_id}")


@app.get("/graph/animated/{run_id}", response_class=HTMLResponse)
def get_animated_graph(run_id: Annotated[str, Path(min_length=3)]):
    """Retrieve an ANIMATED visual graph that plays automatically."""
    from fastapi.responses import HTMLResponse
    from visualization.animated_graph import build_animated_graph_page
    
    trace = _orchestrator.load_trace(run_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Convert trace to dict
    trace_data = trace.model_dump()
    html_content = build_animated_graph_page(trace_data)
    return HTMLResponse(content=html_content)


@app.get("/graph/live", response_class=HTMLResponse)
def get_latest_live_graph():
    """Get a live-updating graph page for the most recent run."""
    from pathlib import Path
    from fastapi.responses import RedirectResponse
    
    # Find the most recent run directory
    runs_dir = Path(__file__).resolve().parent.parent / "data" / "runs"
    if not runs_dir.exists():
        raise HTTPException(status_code=404, detail="No runs found")
    
    run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
    if not run_dirs:
        raise HTTPException(status_code=404, detail="No runs found")
    
    latest_run_dir = max(run_dirs, key=lambda d: d.stat().st_mtime)
    run_id = latest_run_dir.name
    
    # Redirect to the live graph for this run
    return RedirectResponse(url=f"/graph/live/{run_id}")


@app.get("/graph/live/{run_id}", response_class=HTMLResponse)
def get_live_graph(run_id: Annotated[str, Path(min_length=3)]):
    """Get a live-updating graph page for an ongoing run."""
    from visualization.live_graph import build_live_html_page
    html_content = build_live_html_page()
    return HTMLResponse(content=html_content)


@app.get("/graph", response_class=HTMLResponse)
def get_latest_graph():
    """Retrieve a visual graph of the most recent run."""
    from fastapi.responses import HTMLResponse
    from visualization.graph_builder import build_html_page
    import os
    from pathlib import Path
    
    # Find the most recent run directory
    runs_dir = Path(__file__).resolve().parent.parent / "data" / "runs"
    if not runs_dir.exists():
        raise HTTPException(status_code=404, detail="No runs found")
    
    # Get all run directories sorted by modification time (most recent first)
    run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
    if not run_dirs:
        raise HTTPException(status_code=404, detail="No runs found")
    
    latest_run_dir = max(run_dirs, key=lambda d: d.stat().st_mtime)
    run_id = latest_run_dir.name
    
    trace = _orchestrator.load_trace(run_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Latest run trace not found")
    
    # Convert trace to dict
    trace_data = trace.model_dump()
    html_content = build_html_page(trace_data)
    return HTMLResponse(content=html_content)


@app.get("/graph/{run_id}", response_class=HTMLResponse)
def get_graph(run_id: Annotated[str, Path(min_length=3)]):
    """Retrieve a visual graph of the agent conversation flow."""
    from fastapi.responses import HTMLResponse
    from visualization.graph_builder import build_html_page
    
    trace = _orchestrator.load_trace(run_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Convert trace to dict
    trace_data = trace.model_dump()
    html_content = build_html_page(trace_data)
    return HTMLResponse(content=html_content)


@app.get("/graph/live/{run_id}/stream")
async def stream_graph_updates(run_id: Annotated[str, Path(min_length=3)]):
    """Stream live updates for the graph visualization using Server-Sent Events."""
    from fastapi.responses import StreamingResponse
    from pathlib import Path
    import asyncio
    import json
    from visualization.live_graph import generate_sse_update
    
    async def event_generator():
        """Generate SSE events by monitoring the trace file."""
        runs_dir = Path(__file__).resolve().parent.parent / "data" / "runs"
        trace_file = runs_dir / run_id / "trace.json"
        
        if not trace_file.exists():
            yield generate_sse_update("error", {"message": "Run not found"})
            return
        
        last_message_count = 0
        max_checks = 600  # 10 minutes max (600 * 1 second)
        check_count = 0
        
        # Send initial event
        try:
            with open(trace_file, 'r', encoding='utf-8') as f:
                trace_data = json.load(f)
                topic = trace_data.get('topic', 'Research in progress...')
                yield generate_sse_update("init", {"topic": topic})
        except Exception as e:
            yield generate_sse_update("error", {"message": str(e)})
            return
        
        # Poll for updates
        while check_count < max_checks:
            try:
                if not trace_file.exists():
                    yield generate_sse_update("error", {"message": "Trace file disappeared"})
                    return
                
                with open(trace_file, 'r', encoding='utf-8') as f:
                    trace_data = json.load(f)
                
                messages = trace_data.get('messages', [])
                current_message_count = len(messages)
                
                # Send new messages
                if current_message_count > last_message_count:
                    for i in range(last_message_count, current_message_count):
                        msg = messages[i]
                        yield generate_sse_update("message", {
                            "role": msg.get('role', ''),
                            "content": msg.get('content', '')[:200],  # First 200 chars for preview
                            "index": i
                        })
                    last_message_count = current_message_count
                
                # Check if run is complete
                final_insight = trace_data.get('final_insight')
                if final_insight and final_insight.get('status') == 'complete':
                    yield generate_sse_update("complete", {
                        "message": "Run completed successfully",
                        "total_messages": current_message_count
                    })
                    return
                
                await asyncio.sleep(0.3)  # Check every 300ms for faster updates
                check_count += 1
                
            except json.JSONDecodeError:
                # File might be being written, wait and try again
                await asyncio.sleep(0.5)
            except Exception as e:
                yield generate_sse_update("error", {"message": str(e)})
                return
        
        # Timeout
        yield generate_sse_update("complete", {"message": "Monitoring timeout"})
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for nginx
        }
    )


@app.get("/debug/config")
def debug_config() -> dict:
    """Non-sensitive configuration summary to help diagnose setup.

    Does not return secrets. Indicates which provider is active, which model,
    and whether BM25 is enabled with how many chunks.
    """
    import os as _os

    provider = _os.getenv("LLM_PROVIDER") or (
        "gemini" if _os.getenv("GEMINI_API_KEY") else (
            "groq" if _os.getenv("GROQ_API_KEY") else (
                "grok" if _os.getenv("GROK_API_KEY") else "mock"
            )
        )
    )
    model = _os.getenv("MODEL_NAME", "")

    # Inspect reader retriever
    retriever_info = {"enabled": False, "files_dir": _os.getenv("BM25_FILES_DIR", "files"), "chunks": 0}
    try:
        reader = getattr(_orchestrator, "reader", None)
        r = getattr(reader, "_retriever", None)
        if r is not None and hasattr(r, "chunks"):
            retriever_info["enabled"] = True
            retriever_info["chunks"] = len(getattr(r, "chunks", []) or [])
    except Exception:
        pass

    return {
        "provider": provider,
        "model": model,
        "bm25": retriever_info,
        "require_provider": (_os.getenv("REQUIRE_PROVIDER", "false").lower() == "true"),
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("api.server:app", host="0.0.0.0", port=port, reload=False)
