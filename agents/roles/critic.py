"""Critic agent: finds contradictions & missing evidence."""
from __future__ import annotations

from agents.base_agent import BaseAgent, default_agent_config


class CriticAgent(BaseAgent):
    """Surfaces contradictions, gaps, and missing citations/evidence."""

    def __init__(self) -> None:
        super().__init__(
            default_agent_config(
                role_name="critic",
                instructions=(
                    "Challenge claims by identifying contradictions and unsupported points."
                    " List missing evidence and questions for clarification."
                ),
            )
        )

    def role_prompt(self) -> str:  # noqa: D401
        return self.config.instructions
