"""Run a single mock orchestration and print the run_id."""
from __future__ import annotations

from pathlib import Path
import sys

# Ensure project root is on sys.path when running from examples/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestrator.graph import Orchestrator, DATA_ROOT


def main() -> None:
    orch = Orchestrator()
    run_id = orch.run(
        topic="What are effective evaluation methods for LLM-based code assistants?",
        max_turns=2,
        consensus_threshold=0.8,
    )
    print(f"Run completed. run_id={run_id}")
    print(f"Artifacts written to: {DATA_ROOT / run_id}")


if __name__ == "__main__":
    main()
