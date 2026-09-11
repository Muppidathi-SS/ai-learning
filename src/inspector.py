"""
Inspection View for Week 4 — Failure Labeling

For every missed question (correct chunk not in top-3), the inspector:
1. Shows what the retriever actually returned
2. Checks whether the correct chunk exists ANYWHERE in the full ranked list  
3. Labels the failure:
   - R  (Retrieval): correct chunk not in top-3 — retrieval fetched bad context
   - G  (Generation): correct chunk IS in top-3 — model misused good context
   - Not-In-Corpus: the answer doesn't exist in any indexed chunk
"""

from typing import List, Dict, Any, Optional


class InspectionView:
    """
    Diagnoses WHY a retrieval miss happened.
    
    Key principle: you must open the inspection view before labeling.
    "The answer was wrong" is NOT enough to label R — the parameter table
    might be sitting in the top-3 and the model just misread it (that's G).
    """
    
    def __init__(self, all_chunks: List[Dict[str, Any]]):
        """
        Args:
            all_chunks: The full list of indexed chunks (to check if correct chunk exists at all)
        """
        self.all_chunks = all_chunks
        self.chunk_id_set = {c["chunk_id"] for c in all_chunks}

    def inspect(
        self,
        question_id: str,
        question_text: str,
        correct_chunk_id: str,
        retrieved_top3: List[Dict[str, Any]],
        full_retrieved: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Inspect a single question's retrieval result and label the failure type.
        
        Args:
            question_id: e.g., "G01"
            question_text: the question string
            correct_chunk_id: the known-correct chunk_id from golden set
            retrieved_top3: the top-3 results returned by retriever
            full_retrieved: a larger set (e.g., top-25) to check if correct is further down
            
        Returns:
            Dict with label (R/G/Not-In-Corpus), evidence, and diagnostic info
        """
        # Check 1: Does the correct chunk even exist in the corpus?
        if correct_chunk_id not in self.chunk_id_set:
            return {
                "question_id": question_id,
                "question": question_text,
                "label": "Not-In-Corpus",
                "evidence": f"chunk_id '{correct_chunk_id}' does not exist in any indexed chunk",
                "correct_in_top3": False,
                "correct_rank_in_full": None,
                "top3_chunk_ids": [r["chunk_id"] for r in retrieved_top3]
            }

        # Check 2: Is the correct chunk in the top-3?
        top3_ids = [r["chunk_id"] for r in retrieved_top3]
        if correct_chunk_id in top3_ids:
            # The correct chunk IS in top-3 — if the answer is wrong, it's G
            correct_rank = top3_ids.index(correct_chunk_id) + 1
            return {
                "question_id": question_id,
                "question": question_text,
                "label": "G",
                "evidence": f"Correct chunk '{correct_chunk_id}' IS at rank {correct_rank} in top-3 — if answer is wrong, model misused good context",
                "correct_in_top3": True,
                "correct_rank_in_full": correct_rank,
                "top3_chunk_ids": top3_ids
            }

        # Check 3: The correct chunk is NOT in top-3 — check where it is
        full_ids = [r["chunk_id"] for r in full_retrieved]
        if correct_chunk_id in full_ids:
            actual_rank = full_ids.index(correct_chunk_id) + 1
            # Show what DID rank in top-3 instead
            top3_snippets = []
            for r in retrieved_top3:
                snippet = r["content"][:80].replace("\n", " ")
                top3_snippets.append(f"[{r['chunk_id']}] score={r['score']}: {snippet}...")
            
            return {
                "question_id": question_id,
                "question": question_text,
                "label": "R",
                "evidence": (
                    f"Correct chunk '{correct_chunk_id}' exists but ranked #{actual_rank}, "
                    f"outside top-3. Top-3 contained: {', '.join(top3_ids)}"
                ),
                "correct_in_top3": False,
                "correct_rank_in_full": actual_rank,
                "top3_chunk_ids": top3_ids,
                "top3_details": top3_snippets
            }
        else:
            # Correct chunk exists in index but didn't appear in expanded retrieval either
            return {
                "question_id": question_id,
                "question": question_text,
                "label": "R",
                "evidence": (
                    f"Correct chunk '{correct_chunk_id}' exists in corpus but not in top-{len(full_retrieved)} results. "
                    f"Dense retrieval completely missed it. Top-3: {', '.join(top3_ids)}"
                ),
                "correct_in_top3": False,
                "correct_rank_in_full": None,
                "top3_chunk_ids": top3_ids
            }
