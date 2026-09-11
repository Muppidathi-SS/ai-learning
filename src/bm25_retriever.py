"""
BM25 Sparse Retriever for Week 4 — Hybrid Retrieval

Uses rank_bm25 (Okapi BM25) for exact token matching.
Dense embeddings struggle with underscore_case symbols like retry_backoff_ms,
error codes like TimeoutError, and version strings like v3.2.0.
BM25 matches these EXACTLY because it operates on raw tokens, not learned embeddings.
"""

import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi


def tokenize(text: str) -> List[str]:
    """
    Simple whitespace + punctuation tokenizer.
    Keeps underscores intact so parameter names like retry_backoff_ms
    are preserved as single tokens (which is exactly the point of BM25).
    """
    # Lowercase, split on whitespace and punctuation (but keep underscores)
    text = text.lower()
    tokens = re.findall(r'[a-z0-9_]+(?:\.[a-z0-9_]+)*', text)
    return tokens


class BM25Retriever:
    """
    Sparse BM25 retriever over pre-chunked documents.
    
    This retriever tokenizes each chunk at index time and uses BM25Okapi
    to score queries at search time. Unlike dense retrieval, BM25 matches
    exact tokens — making it ideal for symbol names, error codes, and
    configuration literals that embedding models treat as noise subwords.
    """
    
    def __init__(self, chunks: List[Dict[str, Any]]):
        self.chunks = chunks
        # Tokenize all chunks for BM25 indexing
        self.tokenized_corpus = [tokenize(c["content"]) for c in chunks]
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        else:
            self.bm25 = None

    def search(
        self,
        query: str,
        top_k: int = 25,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for top_k most relevant chunks using BM25 scoring.
        
        Returns ranked results with BM25 scores.
        Supports optional metadata filtering (e.g., sdk_version="v3").
        """
        if not self.bm25 or not self.chunks:
            return []

        query_tokens = tokenize(query)
        scores = self.bm25.get_scores(query_tokens)

        # Build candidate list with optional metadata filter
        candidates = []
        for idx, chunk in enumerate(self.chunks):
            if filter_dict:
                match = True
                for key, val in filter_dict.items():
                    if chunk["metadata"].get(key) != val:
                        match = False
                        break
                if not match:
                    continue
            candidates.append((idx, float(scores[idx])))

        # Sort by BM25 score descending
        candidates.sort(key=lambda x: x[1], reverse=True)

        results = []
        for rank, (idx, score) in enumerate(candidates[:top_k], 1):
            chunk_copy = self.chunks[idx].copy()
            chunk_copy["score"] = round(score, 4)
            chunk_copy["rank"] = rank
            results.append(chunk_copy)

        return results
