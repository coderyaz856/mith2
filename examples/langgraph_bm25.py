"""
LangGraph + BM25 example using Groq (ChatGroq) LLM.

- Loads PDFs from ./files (or BM25_FILES_DIR)
- Builds BM25 index
- Runs a 3-node LangGraph pipeline: researcher -> reviewer -> synthesizer
- Reads GROQ_API_KEY and MODEL_NAME from environment (defaults model if unset)

Ensure project root is on sys.path when executing from examples/.
"""
from __future__ import annotations

import os
from typing import List, Dict, Any, Optional, TypedDict

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langchain_groq import ChatGroq
from langgraph.graph import StateGraph

from retrieval.bm25 import BM25Retriever, load_and_chunk_pdfs


class ResearchState(TypedDict):
    topic: str
    summary: Optional[str]
    critique: Optional[str]
    insight: Optional[str]
    sources: Optional[List[str]]


def build_retriever() -> Optional[BM25Retriever]:
    files_dir = os.getenv("BM25_FILES_DIR", "files")
    chunks = load_and_chunk_pdfs(files_dir)
    if not chunks:
        return None
    return BM25Retriever(chunks)


def researcher_agent(state: ResearchState, retriever: Optional[BM25Retriever]):
    topic = (state.get("topic") or "").strip()
    if not topic:
        return {"summary": "No topic provided."}
    if not retriever:
        return {"summary": "No documents indexed for retrieval."}
    docs = retriever.get_relevant_documents(topic, k=4)
    if not docs:
        return {"summary": "No relevant documents found."}

    context_pieces = []
    sources: List[str] = []
    for d in docs:
        snippet = d.page_content.strip()
        if len(snippet) > 800:
            snippet = snippet[:800].rsplit(" ", 1)[0] + " ..."
        source = d.metadata.get("source", "unknown")
        chunk_id = d.metadata.get("chunk_id", "")
        context_pieces.append(f"[SOURCE: {source} | CHUNK: {chunk_id}]\n{snippet}")
        sources.append(source)

    context = "\n\n---\n\n".join(context_pieces)
    prompt = (
        f"You are a research assistant. The user asked about: '{topic}'.\n\n"
        f"Read the following retrieved excerpts (lexical retrieval via BM25) and produce a concise summary "
        f"of the main findings or facts relevant to the topic. Be explicit about which sources support which points.\n\n"
        f"EXCERPTS:\n\n{context}\n\n"
        "Return a short summary and a short list of (source -> supporting sentence)."
    )
    llm = ChatGroq(model=os.getenv("MODEL_NAME", "llama-3.3-70b-versatile"), temperature=0)
    resp = llm.invoke(prompt)
    summary_text = getattr(resp, "content", None) or str(resp)
    return {"summary": summary_text, "sources": list(dict.fromkeys(sources))}


def reviewer_agent(state: ResearchState):
    summary = state.get("summary", "") or ""
    if not summary:
        return {"critique": "No summary to review."}
    prompt = (
        "You are a critical reviewer. Read the following summary and point out: "
        "1) statements that lack direct support from the provided excerpts, "
        "2) possible biases or missing considerations, and "
        "3) questions or follow-ups to verify the claims.\n\n"
        f"SUMMARY:\n\n{summary}\n\n"
        "Give your critique in bullet points."
    )
    llm = ChatGroq(model=os.getenv("MODEL_NAME", "llama-3.3-70b-versatile"), temperature=0)
    resp = llm.invoke(prompt)
    critique_text = getattr(resp, "content", None) or str(resp)
    return {"critique": critique_text}


def synthesizer_agent(state: ResearchState):
    summary = state.get("summary", "") or ""
    critique = state.get("critique", "") or ""
    sources = state.get("sources", []) or []
    prompt = (
        "You are a synthesizer. Combine the summary and critique into a 'Collective Insight Report'. "
        "Include: a 2-3 sentence insight, 2 testable hypotheses or follow-up experiments, and which sources "
        "would be most relevant to test those hypotheses. Keep it concise.\n\n"
        f"SUMMARY:\n{summary}\n\nCRITIQUE:\n{critique}\n\nSOURCES:\n{', '.join(sources)}"
    )
    llm = ChatGroq(model=os.getenv("MODEL_NAME", "llama-3.3-70b-versatile"), temperature=0)
    resp = llm.invoke(prompt)
    insight_text = getattr(resp, "content", None) or str(resp)
    return {"insight": insight_text}


def main() -> None:
    print("📥 Ingesting PDFs and building BM25 index...")
    retriever = build_retriever()
    if retriever:
        print("✅ BM25 index ready.")
    else:
        print("❌ BM25 retriever not created (no chunks). Add PDFs to 'files/'")

    graph = StateGraph(ResearchState)
    graph.add_node("researcher", lambda s: researcher_agent(s, retriever))
    graph.add_node("reviewer", reviewer_agent)
    graph.add_node("synthesizer", synthesizer_agent)
    graph.add_edge("researcher", "reviewer")
    graph.add_edge("reviewer", "synthesizer")
    graph.set_entry_point("researcher")
    app = graph.compile()

    print("🤖 LangGraph (BM25) research lab ready.")
    try:
        while True:
            topic = input("\nEnter a research topic (or 'exit' to quit): ").strip()
            if topic.lower() in ("exit", "quit"):
                break
            print("\nRunning agents pipeline (researcher -> reviewer -> synthesizer)...\n")
            result = app.invoke({"topic": topic})
            print("\n" + "=" * 80 + "\n")
            print(f"Topic: {topic}\n")
            print("📘 Researcher Summary:\n")
            print(result.get("summary", "—"))
            print("\n" + "=" * 80 + "\n")
            print("🔍 Reviewer Critique:\n")
            print(result.get("critique", "—"))
            print("\n" + "=" * 80 + "\n")
            print("💡 Collective Insight:\n")
            print(result.get("insight", "—"))
            print("\n" + "=" * 80 + "\n")
            print("📚 Sources used:", ", ".join(result.get("sources", [])))
            print("\n" + "=" * 80 + "\n")
    except KeyboardInterrupt:
        print("\nExiting.")


if __name__ == "__main__":
    main()
