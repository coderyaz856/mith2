"""Reader agent: extracts key methods & findings from source material."""
from __future__ import annotations

from agents.base_agent import BaseAgent, default_agent_config
from typing import Optional, TYPE_CHECKING, List, Dict, Any
import json
from pathlib import Path

if TYPE_CHECKING:  # pragma: no cover
    from retrieval.bm25 import BM25Retriever


class ReaderAgent(BaseAgent):
    """Extracts salient methodologies, datasets, and findings.

    Optionally prepends:
    - Retrieved BM25 context if a retriever is provided
    - Extracted knowledge base from ingested articles
    """

    def __init__(
        self, 
        retriever: Optional["BM25Retriever"] = None, 
        bm25_k: int = 4,
        knowledge_base_path: Optional[str] = None
    ) -> None:
        super().__init__(
            default_agent_config(
                role_name="reader",
                instructions=(
                    "Identify core methods, datasets, and principal findings."
                    " Provide concise bullet points; avoid speculation."
                    " When available, reference the extracted knowledge base and retrieved documents."
                ),
            )
        )
        self._retriever = retriever
        self._bm25_k = max(1, int(bm25_k))
        self._knowledge_base = self._load_knowledge_base(knowledge_base_path)

    def _load_knowledge_base(self, kb_path: Optional[str]) -> List[Dict[str, Any]]:
        """Load the extracted knowledge base if it exists."""
        if kb_path is None:
            kb_path = "data/knowledge_base.json"
        
        kb_file = Path(kb_path)
        if not kb_file.exists():
            return []
        
        try:
            with open(kb_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def role_prompt(self) -> str:  # noqa: D401
        return self.config.instructions

    def send(self, prompt: str):  # type: ignore[override]
        context_parts = []
        
        # 1. Add knowledge base if available
        if self._knowledge_base:
            kb_context = self._format_knowledge_base()
            if kb_context:
                context_parts.append("--- Extracted Knowledge Base ---\n" + kb_context)
        
        # 2. Add BM25 retrieval if available
        if self._retriever:
            docs = self._retriever.get_relevant_documents(prompt, k=self._bm25_k)
            if docs:
                ctx = []
                for d in docs:
                    snippet = d.page_content.strip()
                    if len(snippet) > 400:
                        snippet = snippet[:400].rsplit(" ", 1)[0] + " ..."
                    ctx.append(
                        f"[SOURCE: {d.metadata.get('source','?')} | CHUNK: {d.metadata.get('chunk_id','?')}]\n{snippet}"
                    )
                context_parts.append("--- Retrieved Document Chunks ---\n" + "\n\n".join(ctx))
        
        # 3. Build augmented prompt
        if context_parts:
            augmented = (
                prompt
                + "\n\n" + "\n\n".join(context_parts)
                + "\n" + "-" * 50 + "\n"
            )
            return super().send(augmented)
        
        return super().send(prompt)
    
    def _format_knowledge_base(self) -> str:
        """Format knowledge base for inclusion in prompt."""
        if not self._knowledge_base:
            return ""
        
        formatted = []
        for i, doc_knowledge in enumerate(self._knowledge_base[:3], 1):  # Limit to first 3 documents
            parts = [f"Document {i}: {doc_knowledge.get('source', 'Unknown')}"]
            
            if doc_knowledge.get('title'):
                parts.append(f"  Title: {doc_knowledge['title']}")
            
            if doc_knowledge.get('summary'):
                summary = doc_knowledge['summary']
                if len(summary) > 300:
                    summary = summary[:300] + "..."
                parts.append(f"  Summary: {summary}")
            
            if doc_knowledge.get('key_concepts'):
                concepts = doc_knowledge['key_concepts'][:5]
                parts.append(f"  Key Concepts: {', '.join(concepts)}")
            
            if doc_knowledge.get('main_findings'):
                findings = doc_knowledge['main_findings'][:3]
                parts.append("  Main Findings:")
                for finding in findings:
                    finding_text = finding if len(finding) < 150 else finding[:150] + "..."
                    parts.append(f"    - {finding_text}")
            
            if doc_knowledge.get('methodologies'):
                methods = doc_knowledge['methodologies'][:3]
                parts.append(f"  Methodologies: {', '.join(methods)}")
            
            formatted.append("\n".join(parts))
        
        return "\n\n".join(formatted)
