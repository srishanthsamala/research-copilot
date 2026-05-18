# ============================================================
# faiss_store.py — FAISS vector store for paper chunk retrieval
# Local, fast, no external service needed.
# ============================================================
import os
import json
import pickle
import numpy as np
import faiss
from typing import List, Dict
from config import TOP_K_RESULTS


class FAISSVectorStore:
    """
    FAISS-based vector store for storing and retrieving paper chunks.
    Each session builds a fresh in-memory index for the fetched papers.
    """

    def __init__(self, dimension: int = 384):
        """
        Args:
            dimension: Embedding size (384 for all-MiniLM-L6-v2)
        """
        self.dimension  = dimension
        self.index      = faiss.IndexFlatIP(dimension)  # Inner product (cosine with normalized vecs)
        self.chunks     : List[Dict] = []               # Parallel list of chunk metadata
        self.paper_map  : Dict[str, Dict] = {}          # title → paper metadata

    def add_chunks(self, chunks: List[Dict], embeddings: List[List[float]]):
        """
        Add chunks and their embeddings to the FAISS index.
        Args:
            chunks:     List of chunk dicts with metadata
            embeddings: Corresponding embedding vectors
        """
        if not chunks or not embeddings:
            return

        vectors = np.array(embeddings, dtype=np.float32)

        # Normalize for cosine similarity (already done in Embedder, but ensure)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        vectors = vectors / norms

        self.index.add(vectors)
        self.chunks.extend(chunks)

        # Update paper map
        for chunk in chunks:
            title = chunk.get("paper_title", "")
            if title and title not in self.paper_map:
                self.paper_map[title] = {
                    "title":          chunk["paper_title"],
                    "authors":        chunk["paper_authors"],
                    "year":           chunk["paper_year"],
                    "source":         chunk["paper_source"],
                    "url":            chunk["paper_url"],
                    "doi":            chunk["paper_doi"],
                    "citation_count": chunk["citation_count"],
                }

    def retrieve(self, query_embedding: List[float], top_k: int = TOP_K_RESULTS) -> List[Dict]:
        """
        Retrieve the top_k most relevant chunks for a query embedding.
        Returns chunks sorted by relevance with their similarity scores.
        """
        if self.index.ntotal == 0:
            return []

        query_vec = np.array([query_embedding], dtype=np.float32)
        # Normalize query vector
        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec = query_vec / norm

        k          = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query_vec, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            chunk = self.chunks[idx].copy()
            chunk["relevance_score"] = float(score)
            results.append(chunk)

        return results

    def get_all_papers(self) -> List[Dict]:
        """Return metadata for all unique papers in the store."""
        return list(self.paper_map.values())

    def get_paper_count(self) -> int:
        """Return number of unique papers indexed."""
        return len(self.paper_map)

    def get_chunk_count(self) -> int:
        """Return total number of chunks indexed."""
        return self.index.ntotal

    def clear(self):
        """Reset the vector store (for new queries)."""
        self.index  = faiss.IndexFlatIP(self.dimension)
        self.chunks = []
        self.paper_map = {}
        print("[FAISSStore] Index cleared.")
