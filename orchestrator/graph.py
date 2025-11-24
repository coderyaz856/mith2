"""
Orchestration graph coordinating message flow among agents.

Implements a simple linear pipeline:
Reader -> Critic -> Synthesizer -> Verifier

Stops when either the maximum number of turns is reached or the
Verifier's confidence exceeds a consensus threshold.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
import time
from pathlib import Path
from typing import List, Optional

from agents.roles.reader import ReaderAgent
from agents.roles.critic import CriticAgent
from agents.roles.synthesizer import SynthesizerAgent
from agents.roles.verifier import VerifierAgent
from agents.roles.followup import FollowUpAgent
from schemas.models import InsightReport, Message, Trace, Turn

# Optional BM25 integration
import os
from typing import TYPE_CHECKING
try:  # pragma: no cover
    from retrieval.bm25 import BM25Retriever, load_and_chunk_pdfs
except Exception:  # pragma: no cover
    BM25Retriever = None  # type: ignore
    load_and_chunk_pdfs = None  # type: ignore

DATA_ROOT = Path(__file__).resolve().parent.parent / "data" / "runs"
DATA_ROOT.mkdir(parents=True, exist_ok=True)


class Orchestrator:
    """Coordinates agents and persists trace/report artifacts.

    Supports optional BM25 retrieval at startup and per-run overrides.
    """

    def __init__(self) -> None:
        self.reader = self._init_reader()
        self.critic = CriticAgent()
        self.synthesizer = SynthesizerAgent()
        self.verifier = VerifierAgent()
        self.followup = FollowUpAgent()

    def run(
        self,
        topic: str,
        max_turns: int = 2,
        consensus_threshold: float = 0.8,
        enable_bm25: bool | None = None,
        files_dir: str | None = None,
        bm25_k: int = 4,
    ) -> str:
        """Execute an orchestration run.

        Args:
            topic: Research topic to explore.
            max_turns: Upper bound on pipeline iterations.
            consensus_threshold: Confidence required to stop early.

        Returns:
            run_id: Unique identifier for the persisted trace.
        """
        run_id = str(uuid.uuid4())
        trace = Trace(
            run_id=run_id,
            topic=topic,
            created_at=datetime.utcnow(),
            status="running",
            turns=[],
        )

        # Per-run retrieval override if requested
        if enable_bm25 is not None and BM25Retriever and load_and_chunk_pdfs:
            if enable_bm25:
                use_dir = files_dir or os.getenv("BM25_FILES_DIR", "files")
                chunks = load_and_chunk_pdfs(use_dir)
                override = BM25Retriever(chunks) if chunks else None
                self.reader = self._init_reader(override_retriever=override, bm25_k=bm25_k)
            else:
                self.reader = self._init_reader(override_retriever=None, bm25_k=bm25_k)

        # Optional per-step delay to honor provider rate limits
        step_delay = 0.0
        try:
            step_delay = float(os.getenv("AGENT_STEP_DELAY_S", "0"))
        except Exception:
            step_delay = 0.0

        # Debate settings
        try:
            debate_rounds = max(0, int(os.getenv("DEBATE_ROUNDS", "1")))
        except Exception:
            debate_rounds = 1
        debate_enabled = (os.getenv("DEBATE_ENABLE", "true").lower() == "true") and debate_rounds > 0

        for turn_index in range(max_turns):
            turn_messages: List[Message] = []
            
            # Reader - extracts methods and findings
            reader_msg = self.reader.send(topic if turn_index == 0 else topic)
            turn_messages.append(reader_msg)
            if step_delay:
                time.sleep(step_delay)
            
            # Optional Debate: Reader -> Critic
            critic_handoff_text = reader_msg.content
            if debate_enabled:
                handoff, debate_msgs = self._debate(
                    agent_a=self.reader,
                    agent_b=self.critic,
                    context=reader_msg.content,
                    a_role="reader",
                    b_role="critic",
                    max_rounds=debate_rounds,
                    step_delay=step_delay,
                )
                critic_handoff_text = handoff or reader_msg.content
                # Record debate messages in trace so we can see "who's talking"
                turn_messages.extend(debate_msgs)
                if step_delay:
                    time.sleep(step_delay)

            # Critic - challenges reader's findings using the coherent handoff
            critic_input = (
                f"The Reader has provided the following analysis (after debate handoff):\n\n{critic_handoff_text}\n\n"
                f"Critically evaluate the Reader's findings. Identify gaps, unsupported claims, "
                f"and potential biases. Reference specific points from the Reader's analysis."
            )
            critic_msg = self.critic.send(critic_input)
            turn_messages.append(critic_msg)
            if step_delay:
                time.sleep(step_delay)

            # Optional Debate: Critic -> Synthesizer
            critic_to_synth_text = critic_msg.content
            if debate_enabled:
                handoff, debate_msgs = self._debate(
                    agent_a=self.critic,
                    agent_b=self.synthesizer,
                    context=critic_msg.content,
                    a_role="critic",
                    b_role="synthesizer",
                    max_rounds=debate_rounds,
                    step_delay=step_delay,
                )
                critic_to_synth_text = handoff or critic_msg.content
                turn_messages.extend(debate_msgs)
                if step_delay:
                    time.sleep(step_delay)

            # Synthesizer - integrates reader and critic perspectives (using debated critic text)
            synth_input = (
                f"--- Reader's Analysis ---\n{reader_msg.content}\n\n"
                f"--- Critic's Evaluation (after debate handoff) ---\n{critic_to_synth_text}\n\n"
                f"Synthesize the Reader's findings with the Critic's challenges. "
                f"Generate hypotheses that address the Critic's concerns while building on the Reader's insights. "
                f"Reference specific points from both agents."
            )
            synth_msg = self.synthesizer.send(synth_input)
            turn_messages.append(synth_msg)
            if step_delay:
                time.sleep(step_delay)

            # Optional Debate: Synthesizer -> Verifier
            synth_to_verifier_text = synth_msg.content
            if debate_enabled:
                handoff, debate_msgs = self._debate(
                    agent_a=self.synthesizer,
                    agent_b=self.verifier,
                    context=synth_msg.content,
                    a_role="synthesizer",
                    b_role="verifier",
                    max_rounds=debate_rounds,
                    step_delay=step_delay,
                )
                synth_to_verifier_text = handoff or synth_msg.content
                turn_messages.extend(debate_msgs)
                if step_delay:
                    time.sleep(step_delay)

            # Verifier - assesses synthesis quality (using debated synth text)
            verify_input = (
                f"--- Synthesizer's Hypotheses (after debate handoff) ---\n{synth_to_verifier_text}\n\n"
                f"Verify the Synthesizer's hypotheses against the original evidence. "
                f"Consider the Reader's findings and the Critic's concerns. "
                f"Reference specific hypotheses and explain your confidence assessment."
            )
            verifier_msg = self.verifier.send(verify_input)
            turn_messages.append(verifier_msg)
            if step_delay:
                time.sleep(step_delay)

            # Optional Debate: Verifier -> FollowUp (to ensure coherent context for planning)
            verifier_to_follow_text = verifier_msg.content
            if debate_enabled:
                handoff, debate_msgs = self._debate(
                    agent_a=self.verifier,
                    agent_b=self.followup,
                    context=verifier_msg.content,
                    a_role="verifier",
                    b_role="followup",
                    max_rounds=debate_rounds,
                    step_delay=step_delay,
                )
                verifier_to_follow_text = handoff or verifier_msg.content
                turn_messages.extend(debate_msgs)
                if step_delay:
                    time.sleep(step_delay)

            # FollowUp - proposes next research directions
            followup_input = (
                f"--- Research Context ---\n"
                f"Topic: {topic}\n\n"
                f"Reader's Findings:\n{reader_msg.content[:500]}...\n\n"
                f"Critic's Challenges (debated):\n{critic_to_synth_text[:500]}...\n\n"
                f"Synthesizer's Hypotheses (debated):\n{synth_to_verifier_text[:500]}...\n\n"
                f"Verifier's Assessment (debated, Confidence: {verifier_msg.confidence}):\n{verifier_to_follow_text[:500]}...\n\n"
                f"Based on the complete multi-agent analysis above, propose follow-up research questions "
                f"and identify knowledge gaps. Reference specific findings from each agent."
            )
            followup_msg = self.followup.send(followup_input)
            turn_messages.append(followup_msg)

            trace.turns.append(Turn(index=turn_index, messages=turn_messages))

            if verifier_msg.confidence >= consensus_threshold:
                break

        trace.status = "complete"
        self._persist_trace(trace)
        self._persist_report(trace)
        return run_id

    # -------- Initialization helpers --------
    def _init_reader(self, override_retriever: Optional[object] = None, bm25_k: int = 4) -> ReaderAgent:
        """Initialize ReaderAgent with optional BM25 retriever and knowledge base.

        Activation rules:
          - If env ENABLE_BM25=true AND retrieval modules available AND PDFs present in ./files
          - or if env ENABLE_BM25=auto (default) and PDFs exist
          - Knowledge base path defaults to data/knowledge_base.json if exists
        Returns ReaderAgent (with or without retriever and KB).
        """
        enable = (os.getenv("ENABLE_BM25", "auto").lower())
        retriever = None
        if override_retriever is not None:
            retriever = override_retriever
        elif BM25Retriever and load_and_chunk_pdfs and enable in {"true", "auto"}:
            files_dir = os.getenv("BM25_FILES_DIR", "files")
            chunks = load_and_chunk_pdfs(files_dir)
            if chunks:
                retriever = BM25Retriever(chunks)
        
        # Knowledge base path
        kb_path = os.getenv("KNOWLEDGE_BASE_PATH", "data/knowledge_base.json")
        
        return ReaderAgent(retriever=retriever, bm25_k=bm25_k, knowledge_base_path=kb_path)

    # -------- Debate helper --------
    def _debate(
        self,
        agent_a,
        agent_b,
        context: str,
        a_role: str,
        b_role: str,
        max_rounds: int = 1,
        step_delay: float = 0.0,
    ) -> tuple[str, list[Message]]:
        """Run a short clarification debate from agent A to agent B.

        The pattern per round:
          1) B asks up to 3 clarifying questions about A's content
          2) A answers concisely
          3) B produces a short coherent summary ending with [DONE] if sufficient else [MORE]

        Returns (handoff_text_for_b, debate_messages)
        """
        debate_messages: list[Message] = []
        latest_summary = ""

        for r in range(1, max_rounds + 1):
            # B asks questions
            b_q_prompt = (
                f"As the {b_role.upper()}, before proceeding, read the following {a_role.upper()}'s output "
                f"and ask up to 3 clarifying questions you need to form a coherent understanding.\n\n"
                f"=== {a_role.upper()} OUTPUT ===\n{context}\n\n"
                f"Return ONLY a numbered list of questions."
            )
            b_q_msg = agent_b.send(b_q_prompt)
            b_q_msg.content = f"[DEBATE {a_role}->{b_role} | {b_role.upper()} asks | Round {r}]\n" + b_q_msg.content
            debate_messages.append(b_q_msg)
            if step_delay:
                time.sleep(step_delay)

            # A answers
            a_ans_prompt = (
                f"As the {a_role.upper()}, answer the following questions clearly and concisely, "
                f"filling any missing details from your analysis. If a question is outside your scope, say so.\n\n"
                f"=== QUESTIONS FROM {b_role.upper()} (Round {r}) ===\n{b_q_msg.content}\n\n"
                f"Provide numbered answers."
            )
            a_ans_msg = agent_a.send(a_ans_prompt)
            a_ans_msg.content = f"[DEBATE {a_role}->{b_role} | {a_role.upper()} answers | Round {r}]\n" + a_ans_msg.content
            debate_messages.append(a_ans_msg)
            if step_delay:
                time.sleep(step_delay)

            # B synthesizes understanding and signals readiness
            b_sum_prompt = (
                f"As the {b_role.upper()}, produce a concise coherent summary of your understanding "
                f"incorporating the answers. End the message with either [DONE] if you have enough to proceed, "
                f"or [MORE] if you still need clarification."
                f"\n\n=== {a_role.upper()} ORIGINAL OUTPUT ===\n{context}\n\n"
                f"=== {a_role.upper()} ANSWERS (Round {r}) ===\n{a_ans_msg.content}\n"
            )
            b_sum_msg = agent_b.send(b_sum_prompt)
            b_sum_msg.content = f"[DEBATE {a_role}->{b_role} | {b_role.upper()} synthesis | Round {r}]\n" + b_sum_msg.content
            debate_messages.append(b_sum_msg)
            latest_summary = b_sum_msg.content
            if step_delay:
                time.sleep(step_delay)

            # Check readiness
            if "[done]" in b_sum_msg.content.lower():
                break

        # Handoff text is B's final synthesis without the debate header prefix
        handoff_text = latest_summary.split("\n", 1)[-1] if latest_summary else context
        return handoff_text, debate_messages

    # -------- Persistence --------
    def _persist_trace(self, trace: Trace) -> None:
        run_dir = DATA_ROOT / trace.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        trace_path = run_dir / "trace.json"
        with trace_path.open("w", encoding="utf-8") as f:
            json.dump(trace.model_dump(), f, indent=2, default=str)

    def _persist_report(self, trace: Trace) -> None:
        # Build a report using last synthesizer, verifier, and followup messages.
        last_turn = trace.turns[-1]
        synth = next((m for m in last_turn.messages if m.role == "synthesizer"), None)
        verifier = next((m for m in last_turn.messages if m.role == "verifier"), None)
        followup = next((m for m in last_turn.messages if m.role == "followup"), None)
        
        hypotheses: List[str] = []
        if synth:
            # Split mock hypotheses by sentences (placeholder logic).
            hypotheses = [h.strip() for h in synth.content.split(".") if h.strip()][:5]
        
        citations = []
        if synth:
            citations.extend(synth.citations)
        if verifier:
            citations.extend(verifier.citations)
        if followup:
            citations.extend(followup.citations)
        
        # Build summary with followup questions if available
        summary = synth.content[:300] if synth else ""
        if followup:
            summary += f"\n\nFollow-up Research Directions:\n{followup.content[:200]}..."
        
        report = InsightReport(
            run_id=trace.run_id,
            topic=trace.topic,
            summary=summary,
            hypotheses=hypotheses,
            confidence=(verifier.confidence if verifier else 0.0),
            citations=citations,
        )
        run_dir = DATA_ROOT / trace.run_id
        report_path = run_dir / "report.json"
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2)

    # -------- Loaders --------
    def load_trace(self, run_id: str) -> Trace | None:
        path = DATA_ROOT / run_id / "trace.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return Trace(**data)

    def load_report(self, run_id: str) -> InsightReport | None:
        path = DATA_ROOT / run_id / "report.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return InsightReport(**data)
