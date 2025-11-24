"""Knowledge extraction from research papers and articles using LLM.

This module analyzes documents to extract:
- Key concepts and terminology
- Main findings and conclusions
- Data points and statistics
- Methodologies and approaches
- Citations and references
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path

from retrieval.bm25 import load_and_chunk_pdfs, DocChunk
from integrations.grok_client import LLMClient


@dataclass
class ExtractedKnowledge:
    """Structured knowledge extracted from a document."""
    source: str
    title: Optional[str] = None
    key_concepts: List[str] = None
    main_findings: List[str] = None
    data_points: List[str] = None
    methodologies: List[str] = None
    citations: List[str] = None
    summary: Optional[str] = None
    
    def __post_init__(self):
        if self.key_concepts is None:
            self.key_concepts = []
        if self.main_findings is None:
            self.main_findings = []
        if self.data_points is None:
            self.data_points = []
        if self.methodologies is None:
            self.methodologies = []
        if self.citations is None:
            self.citations = []


class KnowledgeExtractor:
    """Extract structured knowledge from documents using LLM."""
    
    EXTRACTION_PROMPT = """You are an expert research analyst. Analyze the following text excerpt from a research paper or article and extract structured information.

TEXT:
{text}

Extract the following information in JSON format:
{{
  "title": "Document title if mentioned, otherwise null",
  "key_concepts": ["concept1", "concept2", ...],
  "main_findings": ["finding1", "finding2", ...],
  "data_points": ["statistic1", "measurement1", ...],
  "methodologies": ["method1", "approach1", ...],
  "citations": ["reference1", "reference2", ...],
  "summary": "Brief 2-3 sentence summary of the content"
}}

Guidelines:
- key_concepts: Core ideas, theories, terminology, technical terms
- main_findings: Conclusions, results, discoveries, claims
- data_points: Numbers, statistics, measurements, percentages, sample sizes
- methodologies: Research methods, experimental designs, analytical approaches
- citations: Author names, paper titles, years mentioned (format: "Author (Year)")
- summary: High-level overview of what this text is about

Return ONLY valid JSON, no additional text."""

    SYNTHESIS_PROMPT = """You are synthesizing knowledge extracted from multiple chunks of a document.

Here are the extracted facts from different sections:

{chunks_json}

Create a comprehensive synthesis that:
1. Combines and deduplicates information
2. Identifies the main themes
3. Highlights the most important findings
4. Summarizes key data points
5. Lists unique methodologies

Return a JSON object with these fields:
{{
  "title": "Best guess at document title",
  "key_concepts": ["unique concept1", "unique concept2", ...],
  "main_findings": ["consolidated finding1", ...],
  "data_points": ["important statistic1", ...],
  "methodologies": ["method1", ...],
  "citations": ["Author (Year)", ...],
  "summary": "Comprehensive 3-5 sentence summary of the entire document"
}}

Return ONLY valid JSON, no additional text."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize the knowledge extractor.
        
        Args:
            llm_client: LLM client to use. If None, creates a new one.
        """
        self.llm = llm_client or LLMClient()
        logging.info(f"KnowledgeExtractor initialized with provider: {self.llm.provider}")
    
    def extract_from_chunk(self, chunk: DocChunk) -> Dict[str, Any]:
        """Extract knowledge from a single document chunk.
        
        Args:
            chunk: Document chunk to analyze
            
        Returns:
            Dictionary with extracted knowledge
        """
        prompt = self.EXTRACTION_PROMPT.format(text=chunk.page_content[:3000])
        
        try:
            content, _, _ = self.llm.generate(
                instructions="You are a research analyst extracting structured information.",
                prompt=prompt
            )
            
            # Try to parse JSON from response
            content = content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                lines = content.split("\n")
                # Remove first and last lines (``` markers)
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                content = content.replace("```json", "").replace("```", "").strip()
            
            extracted = json.loads(content)
            extracted["source"] = chunk.metadata.get("source", "unknown")
            extracted["chunk_id"] = chunk.metadata.get("chunk_id", "")
            return extracted
            
        except json.JSONDecodeError as e:
            logging.warning(f"Failed to parse JSON from LLM response for chunk {chunk.metadata.get('chunk_id')}: {e}")
            logging.debug(f"Raw response: {content[:200]}...")
            # Return empty structure
            return {
                "source": chunk.metadata.get("source", "unknown"),
                "chunk_id": chunk.metadata.get("chunk_id", ""),
                "key_concepts": [],
                "main_findings": [],
                "data_points": [],
                "methodologies": [],
                "citations": [],
                "summary": content[:200] if content else ""
            }
        except Exception as e:
            logging.error(f"Error extracting from chunk: {e}")
            return {
                "source": chunk.metadata.get("source", "unknown"),
                "chunk_id": chunk.metadata.get("chunk_id", ""),
                "error": str(e)
            }
    
    def synthesize_extractions(self, extractions: List[Dict[str, Any]], source: str) -> ExtractedKnowledge:
        """Synthesize multiple chunk extractions into unified knowledge.
        
        Args:
            extractions: List of extraction dictionaries from chunks
            source: Source document name
            
        Returns:
            Unified ExtractedKnowledge object
        """
        if not extractions:
            return ExtractedKnowledge(source=source)
        
        # If only one extraction, convert directly
        if len(extractions) == 1:
            ext = extractions[0]
            return ExtractedKnowledge(
                source=source,
                title=ext.get("title"),
                key_concepts=ext.get("key_concepts", []),
                main_findings=ext.get("main_findings", []),
                data_points=ext.get("data_points", []),
                methodologies=ext.get("methodologies", []),
                citations=ext.get("citations", []),
                summary=ext.get("summary")
            )
        
        # Multiple extractions - use LLM to synthesize
        chunks_json = json.dumps(extractions, indent=2)
        prompt = self.SYNTHESIS_PROMPT.format(chunks_json=chunks_json)
        
        try:
            content, _, _ = self.llm.generate(
                instructions="You are synthesizing research knowledge from multiple sources.",
                prompt=prompt
            )
            
            # Clean and parse
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                content = content.replace("```json", "").replace("```", "").strip()
            
            synthesized = json.loads(content)
            return ExtractedKnowledge(
                source=source,
                title=synthesized.get("title"),
                key_concepts=synthesized.get("key_concepts", []),
                main_findings=synthesized.get("main_findings", []),
                data_points=synthesized.get("data_points", []),
                methodologies=synthesized.get("methodologies", []),
                citations=synthesized.get("citations", []),
                summary=synthesized.get("summary")
            )
            
        except Exception as e:
            logging.error(f"Error synthesizing extractions: {e}")
            # Fallback: simple concatenation
            return self._simple_synthesis(extractions, source)
    
    def _simple_synthesis(self, extractions: List[Dict[str, Any]], source: str) -> ExtractedKnowledge:
        """Fallback: simple concatenation without LLM synthesis."""
        all_concepts = []
        all_findings = []
        all_data = []
        all_methods = []
        all_citations = []
        summaries = []
        
        for ext in extractions:
            all_concepts.extend(ext.get("key_concepts", []))
            all_findings.extend(ext.get("main_findings", []))
            all_data.extend(ext.get("data_points", []))
            all_methods.extend(ext.get("methodologies", []))
            all_citations.extend(ext.get("citations", []))
            if ext.get("summary"):
                summaries.append(ext["summary"])
        
        # Deduplicate
        return ExtractedKnowledge(
            source=source,
            key_concepts=list(set(all_concepts)),
            main_findings=list(set(all_findings)),
            data_points=list(set(all_data)),
            methodologies=list(set(all_methods)),
            citations=list(set(all_citations)),
            summary=" | ".join(summaries[:3]) if summaries else None
        )
    
    def process_document(
        self,
        chunks: List[DocChunk],
        max_chunks: Optional[int] = None
    ) -> ExtractedKnowledge:
        """Process all chunks from a document and extract unified knowledge.
        
        Args:
            chunks: List of chunks from the same document
            max_chunks: Maximum number of chunks to process (None = all)
            
        Returns:
            Unified ExtractedKnowledge
        """
        if not chunks:
            return ExtractedKnowledge(source="unknown")
        
        source = chunks[0].metadata.get("source", "unknown")
        logging.info(f"Processing document: {source} ({len(chunks)} chunks)")
        
        # Limit chunks if specified
        chunks_to_process = chunks[:max_chunks] if max_chunks else chunks
        
        extractions = []
        for i, chunk in enumerate(chunks_to_process):
            logging.info(f"  Extracting from chunk {i+1}/{len(chunks_to_process)}")
            extraction = self.extract_from_chunk(chunk)
            extractions.append(extraction)
        
        logging.info(f"  Synthesizing {len(extractions)} extractions")
        knowledge = self.synthesize_extractions(extractions, source)
        return knowledge
    
    def process_directory(
        self,
        articles_dir: str = "articles",
        max_chunks_per_doc: Optional[int] = 5,
        cache_dir: Optional[str] = None
    ) -> List[ExtractedKnowledge]:
        """Process all PDFs in a directory and extract knowledge.
        
        Args:
            articles_dir: Directory containing PDF files
            max_chunks_per_doc: Max chunks to process per document
            cache_dir: Directory to cache results (None = no caching)
            
        Returns:
            List of ExtractedKnowledge objects, one per document
        """
        logging.info(f"Loading PDFs from {articles_dir}")
        all_chunks = load_and_chunk_pdfs(files_dir=articles_dir)
        
        if not all_chunks:
            logging.warning(f"No chunks loaded from {articles_dir}")
            return []
        
        # Group chunks by source document
        docs_chunks: Dict[str, List[DocChunk]] = {}
        for chunk in all_chunks:
            source = chunk.metadata.get("source", "unknown")
            if source not in docs_chunks:
                docs_chunks[source] = []
            docs_chunks[source].append(chunk)
        
        logging.info(f"Found {len(docs_chunks)} documents with {len(all_chunks)} total chunks")
        
        # Process each document
        results = []
        for source, chunks in docs_chunks.items():
            # Check cache first
            if cache_dir:
                cache_path = Path(cache_dir) / f"{source}.json"
                if cache_path.exists():
                    logging.info(f"Loading cached knowledge for {source}")
                    try:
                        with open(cache_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            knowledge = ExtractedKnowledge(**data)
                            results.append(knowledge)
                            continue
                    except Exception as e:
                        logging.warning(f"Failed to load cache for {source}: {e}")
            
            # Extract knowledge
            knowledge = self.process_document(chunks, max_chunks=max_chunks_per_doc)
            results.append(knowledge)
            
            # Save to cache
            if cache_dir:
                Path(cache_dir).mkdir(parents=True, exist_ok=True)
                cache_path = Path(cache_dir) / f"{source}.json"
                try:
                    with open(cache_path, 'w', encoding='utf-8') as f:
                        json.dump(asdict(knowledge), f, indent=2)
                    logging.info(f"Cached knowledge to {cache_path}")
                except Exception as e:
                    logging.warning(f"Failed to cache {source}: {e}")
        
        return results


def save_knowledge_base(knowledge_list: List[ExtractedKnowledge], output_path: str):
    """Save extracted knowledge to a JSON file.
    
    Args:
        knowledge_list: List of ExtractedKnowledge objects
        output_path: Path to output JSON file
    """
    data = [asdict(k) for k in knowledge_list]
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logging.info(f"Saved knowledge base to {output_path} ({len(data)} documents)")


def load_knowledge_base(input_path: str) -> List[ExtractedKnowledge]:
    """Load extracted knowledge from a JSON file.
    
    Args:
        input_path: Path to input JSON file
        
    Returns:
        List of ExtractedKnowledge objects
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [ExtractedKnowledge(**item) for item in data]
