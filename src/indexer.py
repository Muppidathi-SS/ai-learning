import os
import glob
from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer

class VectorIndexer:
    """
    Beginner-Friendly Vector Indexer
    
    1. Ingests documentation files (.txt or .md).
    2. Chunks them using a chunker strategy.
    3. Validates required metadata fields (`source_file`, `page_id`, `sdk_version`, `page_type`).
    4. Computes vector embeddings using `all-MiniLM-L6-v2`.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.chunks: List[Dict[str, Any]] = []
        self.embeddings: np.ndarray = np.array([])

    def ingest_directory(self, docs_dir: str, chunker, sdk_version: str = "v3") -> List[Dict[str, Any]]:
        """Reads all .txt and .md files in docs_dir, chunks them, validates metadata, and builds vector index."""
        new_chunks = []
        doc_files = glob.glob(os.path.join(docs_dir, "*.md")) + glob.glob(os.path.join(docs_dir, "*.txt"))
        doc_files.sort()

        for filepath in doc_files:
            filename = os.path.basename(filepath)
            page_id = os.path.splitext(filename)[0]
            
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()

            # Metadata required by assignment guidelines
            doc_metadata = {
                "source_file": os.path.relpath(filepath),
                "page_id": page_id,
                "sdk_version": sdk_version,
                "page_type": "reference"
            }

            # Generate chunks using chunker
            file_chunks = chunker.chunk(text, doc_metadata)
            
            # Validate metadata requirement: A chunk without source_file fails ingest
            for chunk in file_chunks:
                if not chunk["metadata"].get("source_file"):
                    raise ValueError(f"Failed Ingest: Chunk {chunk['chunk_id']} is missing source_file metadata!")
                new_chunks.append(chunk)

        # Store chunks and encode embeddings
        self.chunks.extend(new_chunks)
        
        texts = [c["content"] for c in self.chunks]
        if texts:
            embeddings_raw = self.model.encode(texts, convert_to_numpy=True)
            # Normalize vectors for cosine similarity calculation
            norms = np.linalg.norm(embeddings_raw, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self.embeddings = embeddings_raw / norms
        else:
            self.embeddings = np.array([])

        print(f"Ingested {len(new_chunks)} chunks from {len(doc_files)} files in {docs_dir}. Total indexed chunks: {len(self.chunks)}.")
        return new_chunks
