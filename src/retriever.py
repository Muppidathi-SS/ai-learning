from typing import List, Dict, Any, Optional
import numpy as np

class VectorRetriever:
    """
    Beginner-Friendly Vector Retriever
    
    Performs cosine similarity search between query vector and indexed document chunks.
    Supports metadata filtering (e.g. filter by `sdk_version = "v3"`).
    """
    def __init__(self, indexer):
        self.indexer = indexer

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Searches for top_k most similar chunks matching optional metadata filter_dict."""
        if len(self.indexer.chunks) == 0:
            return []

        # Step 1: Encode query string into vector and normalize
        query_vec = self.indexer.model.encode([query], convert_to_numpy=True)[0]
        q_norm = np.linalg.norm(query_vec)
        if q_norm > 0:
            query_vec = query_vec / q_norm

        # Step 2: Calculate cosine similarity scores using matrix dot product
        scores = np.dot(self.indexer.embeddings, query_vec)

        # Step 3: Apply metadata filter if provided
        candidate_indices = []
        for idx, chunk in enumerate(self.indexer.chunks):
            if filter_dict:
                match = True
                for key, val in filter_dict.items():
                    if chunk["metadata"].get(key) != val:
                        match = False
                        break
                if not match:
                    continue
            candidate_indices.append(idx)

        if not candidate_indices:
            return []

        # Step 4: Sort matching candidates by score descending
        candidate_scores = [(idx, float(scores[idx])) for idx in candidate_indices]
        candidate_scores.sort(key=lambda x: x[1], reverse=True)

        # Step 5: Format top_k results
        top_results = []
        for rank, (idx, score) in enumerate(candidate_scores[:top_k], 1):
            chunk_copy = self.indexer.chunks[idx].copy()
            chunk_copy["score"] = round(score, 4)
            chunk_copy["rank"] = rank
            top_results.append(chunk_copy)

        return top_results
