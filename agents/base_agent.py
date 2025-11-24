"""
Base agent abstractions and a placeholder Grok API client.

Each role-specific agent should inherit from BaseAgent and supply role
instructions. The send() method composes a role-prefixed prompt and calls
a mock Grok API function to obtain a structured response.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import os
from typing import List, Optional, Tuple
import logging

from schemas.models import Message
import os


@dataclass
class AgentConfig:
    """Configuration for an agent instance."""

    role_name: str
    instructions: str
    model_name: str = "grok-beta"
    api_key: Optional[str] = None


class BaseAgent(ABC):
    """Abstract base class for all agents.

    Subclasses should define role-specific instructions and may override
    pre/post-processing hooks as needed. The default send implementation
    targets a placeholder Grok client to keep the system runnable without
    external dependencies.
    """

    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    @abstractmethod
    def role_prompt(self) -> str:
        """Returns the static system/role prompt for this agent."""

    def send(self, prompt: str) -> Message:
        """Send a prompt to the (mock) Grok API with role instructions.

        Args:
            prompt: The user or upstream agent prompt.

        Returns:
            A Message with role, content, citations, and confidence.
        """
        content, citations, confidence = self._call_grok_api(
            prompt=prompt, instructions=self.role_prompt()
        )
        return Message(
            role=self.config.role_name,
            content=content,
            citations=citations,
            confidence=confidence,
        )

    # -------- Internals / Mock API --------
    def _call_grok_api(self, prompt: str, instructions: str) -> Tuple[str, List[str], float]:
        """Placeholder for calling Grok's API.

        This version is deterministic and offline-friendly. It synthesizes
        content and a pseudo-confidence by hashing the input.

        Environment:
            GROK_API_KEY: If present, indicates a real integration can be wired later.
            MODEL_NAME:   Defaults to "grok-beta".
        """
        # Attempt real Grok call if API key is present; otherwise fallback to mock.
        # Try real provider (Gemini/Groq/Grok) if any relevant env is set.
        require_provider = (os.getenv("REQUIRE_PROVIDER", "false").lower() == "true")
        provider_env_set = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY") or os.getenv("LLM_PROVIDER"))
        if provider_env_set:
            try:
                from integrations.grok_client import LLMClient  # local import to avoid hard dep when mocking

                client = LLMClient()
                return client.generate(instructions=instructions, prompt=prompt)
            except Exception as exc:
                if require_provider:
                    # Surface failure if real provider is required
                    raise
                logging.warning("Provider API call failed, falling back to mock: %s", exc)
        elif require_provider:
            raise RuntimeError("REQUIRE_PROVIDER is true but no provider configuration was found")

        # Fallback: deterministic offline-friendly mock.
        # In a real implementation, you'd use self.config.api_key and self.config.model_name
        # to call the Grok client. For now we generate a simple, reproducible mock.
        seed_src = f"{instructions}\n{prompt}".encode("utf-8")
        h = hashlib.sha256(seed_src).hexdigest()
        # Map a portion of the hash to a confidence in [0.55, 0.95]
        conf_raw = int(h[:8], 16) / 0xFFFFFFFF
        confidence = round(0.55 + 0.4 * conf_raw, 3)

        content = (
            f"[{self.config.role_name.upper()}] {instructions.splitlines()[0].strip()}\n"
            f"Prompt: {prompt}\n"
            f"Response: Based on the provided context, here are the key points and next steps."
        )
        citations = [
            f"mock://ref/{h[0:8]}",
            f"mock://ref/{h[8:16]}",
        ]
        return content, citations, confidence


# Convenience helper to build default agent config from environment

def default_agent_config(role_name: str, instructions: str) -> AgentConfig:
    """Create an AgentConfig using environment variables.

    MODEL_NAME env var defaults to "grok-beta".
    """
    # Prefer GEMINI key if present, then GROQ, then GROK; still optional because BaseAgent
    # will attempt provider call whenever any provider env is set.
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")
    return AgentConfig(
        role_name=role_name,
        instructions=instructions,
        model_name=os.getenv("MODEL_NAME", "grok-beta"),
        api_key=api_key,
    )
