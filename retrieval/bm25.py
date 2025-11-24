"""BM25-based lexical retriever with PDF ingestion.

- Loads PDFs from a directory (default: files/)
- Splits into chunks with metadata (source, chunk_id, orig_page_index)
- Builds a BM25 index using rank_bm25
- Exposes BM25Retriever.get_relevant_documents(query, k)
"""
from __future__ import annotations

import os
import re
import logging
from dataclasses import dataclass
from glob import glob
from typing import Any, Dict, List, Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi


@dataclass
class DocChunk:
    page_content: str
    metadata: Dict[str, Any]


def simple_tokenize(text: str) -> List[str]:
    tokens = re.findall(r"\w+", text.lower())
    return [t for t in tokens if len(t) > 1]


def load_and_chunk_pdfs(
    files_dir: str = "files", chunk_size: int = 1000, chunk_overlap: int = 200
) -> List[DocChunk]:
    chunks: List[DocChunk] = []
    pdf_paths = sorted(glob(os.path.join(files_dir, "*.pdf")))
    if not pdf_paths:
        return []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    for pdf_path in pdf_paths:
        filename = os.path.basename(pdf_path)
        try:
            logging.info(f"Loading PDF: {pdf_path}")
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()
            logging.info(f"Loaded {len(docs)} pages from {filename}")
        except Exception as e:
            # Log the error instead of silently skipping
            logging.error(f"Failed to load {pdf_path}: {e}")
            continue

        for i, d in enumerate(docs):
            if not getattr(d, "metadata", None):
                d.metadata = {}
            d.metadata["source"] = filename
            d.metadata["orig_page_index"] = d.metadata.get("page", i)

        for idx, c in enumerate(splitter.split_documents(docs)):
            meta = dict(c.metadata)
            meta["chunk_id"] = f"{filename}__chunk{idx}"
            chunks.append(DocChunk(page_content=c.page_content, metadata=meta))
    return chunks


class BM25Retriever:
    """Simple BM25 retriever over DocChunk list."""

    def __init__(self, chunks: List[DocChunk]) -> None:
        self.chunks = chunks
        self.tokenized_texts = [simple_tokenize(c.page_content) for c in chunks]
        self.bm25 = BM25Okapi(self.tokenized_texts)

    def get_relevant_documents(self, query: str, k: int = 3) -> List[DocChunk]:
        q_tokens = simple_tokenize(query)
        if not q_tokens:
            return []
        scores = self.bm25.get_scores(q_tokens)
        idx_scores = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        top = [i for i, sc in idx_scores[:k] if sc > 0]
        if not top and idx_scores:
            top = [i for i, _ in idx_scores[:k]]
        return [self.chunks[i] for i in top]
