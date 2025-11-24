"""Verifier agent: re-checks claims to build consensus."""
from __future__ import annotations

from agents.base_agent import BaseAgent, default_agent_config


class VerifierAgent(BaseAgent):
    """Re-checks synthesized claims for internal consistency and evidence sufficiency."""

    def __init__(self) -> None:
        super().__init__(
            default_agent_config(
                role_name="verifier",
                instructions=(
                    "Re-verify claims using available context; flag weak points."
                    " Estimate consensus confidence; propose next step if needed."
                ),
            )
        )

    def role_prompt(self) -> str:  # noqa: D401
        return self.config.instructions
