"""Synthesizer agent: merges insights into candidate hypotheses."""
from __future__ import annotations

from agents.base_agent import BaseAgent, default_agent_config


class SynthesizerAgent(BaseAgent):
    """Combines prior agent outputs into tentative hypotheses and narratives."""

    def __init__(self) -> None:
        super().__init__(
            default_agent_config(
                role_name="synthesizer",
                instructions=(
                    "Integrate findings and critiques into coherent hypotheses."
                    " Provide rationale and map citations to each hypothesis."
                ),
            )
        )

    def role_prompt(self) -> str:  # noqa: D401
        return self.config.instructions
