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


class HybridRetriever:
    """
    Hybrid Retriever using Reciprocal Rank Fusion (RRF).
    
    Combines dense (embedding cosine similarity) and sparse (BM25) retrieval.
    
    WHY RRF and not score averaging:
    - Cosine similarity scores range ~[0.0, 1.0]
    - BM25 scores range ~[0.0, 30.0+] and depend on corpus statistics
    - You CANNOT add or average these — they are on different scales
    - RRF fuses RANKS, not scores: score(d) = Σ 1/(k + rank_i(d))
    - k=60 is the standard dampening constant (Cormack et al. 2009)
    """
    
    def __init__(self, vector_retriever, bm25_retriever, rrf_k: int = 60):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        top_k: int = 3,
        fusion_pool: int = 25,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fuses dense + sparse retrieval results using RRF.
        
        Args:
            query: search query
            top_k: number of final results to return
            fusion_pool: number of candidates to retrieve from EACH retriever before fusion
            filter_dict: optional metadata filter
            
        Returns:
            top_k results ranked by RRF score
        """
        # Step 1: Get candidates from both retrievers
        dense_results = self.vector_retriever.search(query, top_k=fusion_pool, filter_dict=filter_dict)
        sparse_results = self.bm25_retriever.search(query, top_k=fusion_pool, filter_dict=filter_dict)

        # Step 2: Build rank maps (chunk_id -> rank position)
        dense_ranks = {}
        for r in dense_results:
            dense_ranks[r["chunk_id"]] = r["rank"]

        sparse_ranks = {}
        for r in sparse_results:
            sparse_ranks[r["chunk_id"]] = r["rank"]

        # Step 3: Compute RRF score for every unique chunk
        all_chunk_ids = set(dense_ranks.keys()) | set(sparse_ranks.keys())
        
        # Build a lookup for chunk data
        chunk_lookup = {}
        for r in dense_results + sparse_results:
            if r["chunk_id"] not in chunk_lookup:
                chunk_lookup[r["chunk_id"]] = r

        rrf_scores = {}
        for cid in all_chunk_ids:
            score = 0.0
            if cid in dense_ranks:
                score += 1.0 / (self.rrf_k + dense_ranks[cid])
            if cid in sparse_ranks:
                score += 1.0 / (self.rrf_k + sparse_ranks[cid])
            rrf_scores[cid] = score

        # Step 4: Sort by RRF score descending
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # Step 5: Format top_k results
        results = []
        for rank, cid in enumerate(sorted_ids[:top_k], 1):
            chunk_copy = chunk_lookup[cid].copy()
            chunk_copy["score"] = round(rrf_scores[cid], 6)
            chunk_copy["rank"] = rank
            chunk_copy["rrf_score"] = round(rrf_scores[cid], 6)
            # Store component ranks for inspection
            chunk_copy["dense_rank"] = dense_ranks.get(cid, None)
            chunk_copy["sparse_rank"] = sparse_ranks.get(cid, None)
            results.append(chunk_copy)

        return results

    def search_with_mmr(
        self,
        query: str,
        top_k: int = 3,
        fusion_pool: int = 25,
        mmr_lambda: float = 0.7,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        RRF fusion + MMR diversity reranking (Bonus Challenge).
        
        MMR (Maximal Marginal Relevance) balances relevance vs diversity:
        MMR = λ * relevance(d) - (1-λ) * max_similarity(d, selected)
        
        Risk: MMR can push the current version's page OUT of top-3 in the
        name of variety — e.g., if v1, v2, v3 all document Client.send(),
        MMR might pick one of each version instead of the correct v3 page.
        
        Args:
            mmr_lambda: balance between relevance (1.0) and diversity (0.0).
                        Higher = more relevance, lower = more diversity.
        """
        # Get a larger pool of RRF-fused candidates
        candidates = self.search(query, top_k=fusion_pool, fusion_pool=fusion_pool, filter_dict=filter_dict)
        
        if len(candidates) <= top_k:
            return candidates

        # Get embeddings for MMR diversity calculation
        embeddings = self.vector_retriever.indexer.embeddings
        chunk_id_to_idx = {c["chunk_id"]: i for i, c in enumerate(self.vector_retriever.indexer.chunks)}
        
        # Build embedding lookup for candidates
        candidate_embeddings = {}
        for c in candidates:
            idx = chunk_id_to_idx.get(c["chunk_id"])
            if idx is not None:
                candidate_embeddings[c["chunk_id"]] = embeddings[idx]

        # MMR greedy selection
        selected = []
        remaining = list(candidates)
        
        for _ in range(min(top_k, len(candidates))):
            best_score = -float('inf')
            best_idx = 0
            
            for i, cand in enumerate(remaining):
                cid = cand["chunk_id"]
                relevance = cand["rrf_score"]
                
                # Max similarity to already-selected documents
                max_sim = 0.0
                if selected and cid in candidate_embeddings:
                    cand_emb = candidate_embeddings[cid]
                    for sel in selected:
                        sel_id = sel["chunk_id"]
                        if sel_id in candidate_embeddings:
                            sim = float(np.dot(cand_emb, candidate_embeddings[sel_id]))
                            max_sim = max(max_sim, sim)
                
                mmr_score = mmr_lambda * relevance - (1 - mmr_lambda) * max_sim * 0.01
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i
            
            selected.append(remaining.pop(best_idx))
        
        # Re-rank with final positions
        for rank, item in enumerate(selected, 1):
            item["rank"] = rank
        
        return selected
