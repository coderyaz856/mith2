"""
Pydantic data models for Agentic Research Collaborator.

These schemas define the request/response contracts used by the API
and the objects persisted to disk in /data/runs/.

Requires: Python 3.10+, Pydantic v2.
"""
from __future__ import annotations

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class Message(BaseModel):
    """A single agent message.

    Attributes:
        role: The logical role that produced this message (e.g., reader, critic).
        content: Natural language content returned by the agent.
        citations: Optional list of source strings (URLs, DOIs, ids) the agent referenced.
        confidence: A value in [0, 1] indicating the agent's confidence in this message.
    """

    role: str = Field(description="Agent role that produced the message")
    content: str = Field(default="", description="Message content")
    citations: List[str] = Field(default_factory=list, description="Citations referenced by the agent")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score in [0,1]")


class Turn(BaseModel):
    """A single orchestration turn consisting of messages from agents."""

    index: int = Field(ge=0, description="Zero-based turn index")
    messages: List[Message] = Field(default_factory=list, description="Messages in the turn")


class Trace(BaseModel):
    """A full run trace persisted on disk.

    Attributes:
        run_id: Unique identifier for a run.
        topic: Topic provided by the user to investigate.
        created_at: ISO timestamp when the run started.
        status: Simple lifecycle status (e.g., running, complete).
        turns: Ordered turns comprising the conversation among agents.
    """

    run_id: str
    topic: str
    created_at: datetime
    status: str = Field(default="running")
    turns: List[Turn] = Field(default_factory=list)


class InsightReport(BaseModel):
    """Final report produced by the synthesizer/verifier stage."""

    run_id: str
    topic: str
    summary: str = Field(default="", description="High-level narrative of findings")
    hypotheses: List[str] = Field(default_factory=list, description="Candidate hypotheses or insights")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    citations: List[str] = Field(default_factory=list)


# API request/response models
class RunRequest(BaseModel):
    """Body for POST /run"""

    topic: str = Field(min_length=3, description="Research topic to investigate")
    max_turns: int = Field(default=2, ge=1, le=10, description="Maximum number of orchestration turns")
    consensus_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Verifier consensus threshold")
    # Optional retrieval settings (backward compatible)
    enable_bm25: bool | None = Field(default=None, description="Enable BM25 retrieval for this run (overrides env)")
    files_dir: str | None = Field(default=None, description="Directory to scan for PDFs (defaults to env BM25_FILES_DIR or 'files')")
    bm25_k: int = Field(default=4, ge=1, le=20, description="Number of top chunks to retrieve")


class RunResponse(BaseModel):
    """Response for POST /run"""

    run_id: str
