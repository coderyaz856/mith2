"""Quick script to exercise the FastAPI endpoints.

Usage:
  python examples/test_run.py

Requires server running on http://localhost:8080.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict

import httpx

API_BASE = "http://localhost:8080"

TOPIC = "Summarize recent advances in education with LLMs"
MAX_TURNS = 3
CONSENSUS_THRESHOLD = 0.75
ENABLE_BM25 = True  # set True if you added PDFs
FILES_DIR = "articles"  # folder with PDFs if BM25 enabled
BM25_K = 3


def pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)[:4000]  # truncate for console


def main() -> None:
    with httpx.Client(timeout=60) as client:
        payload: Dict[str, Any] = {
            "topic": TOPIC,
            "max_turns": MAX_TURNS,
            "consensus_threshold": CONSENSUS_THRESHOLD,
            "enable_bm25": ENABLE_BM25,
            "files_dir": FILES_DIR,
            "bm25_k": BM25_K,
        }
        print("POST /run payload:\n", pretty(payload))
        resp = client.post(f"{API_BASE}/run", json=payload)
        resp.raise_for_status()
        run_id = resp.json()["run_id"]
        print(f"Run started: {run_id}\n")

        # Trace and insight are written synchronously by orchestrator, small delay just in case
        time.sleep(0.5)

        trace = client.get(f"{API_BASE}/trace/{run_id}").json()
        print("Trace (truncated):\n", pretty(trace))

        insight = client.get(f"{API_BASE}/insight/{run_id}").json()
        print("Insight report:\n", pretty(insight))

        # Quick sanity check for provider vs mock
        joined = " ".join(m.get("content", "") for t in trace.get("turns", []) for m in t.get("messages", []))
        if "mock://" in joined:
            print("WARNING: mock artifacts detected -> provider may not have been used.")
        else:
            print("SUCCESS: No mock:// citations found, provider output looks real.")


if __name__ == "__main__":
    main()
