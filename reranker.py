# ============================================================
# reranker.py — Cross-Encoder Reranker for RAG
#
# Problem with FAISS alone:
#   FAISS uses bi-encoder embeddings — both query and chunk are
#   embedded independently then compared. This misses nuanced
#   query-document interactions.
#
# Solution: Cross-Encoder
#   The cross-encoder sees BOTH the query and each chunk together
#   in a single forward pass, scoring their relevance jointly.
#   This is significantly more accurate than bi-encoder similarity.
#
# Flow:
#   FAISS retrieves top-30 candidates (broad recall)
#   → Cross-encoder scores each against the query
#   → Top-8 by cross-encoder score are passed to LLM
#
# Model: cross-encoder/ms-marco-MiniLM-L-6-v2
#   Fast (CPU), free, state-of-the-art for passage reranking.
# ============================================================
from typing import List, Optional


class CrossEncoderReranker:
    """
    Reranks FAISS-retrieved chunks using a cross-encoder model.
    Falls back to original FAISS order if model unavailable.
    """

    MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(self):
        self._model = None
        self._load_model()

    def _load_model(self):
        """Load cross-encoder. Silently skips if not installed."""
        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.MODEL_NAME, max_length=512)
            print(f"[Reranker] Cross-encoder loaded: {self.MODEL_NAME}")
        except Exception as e:
            print(f"[Reranker] Cross-encoder unavailable ({e}) — using FAISS order.")
            self._model = None

    def rerank(
        self,
        query:   str,
        chunks:  List[dict],
        top_k:   int = 8,
    ) -> List[dict]:
        """
        Rerank chunks by cross-encoder relevance to query.

        Args:
            query:  User's original question
            chunks: Candidate chunks from FAISS (+ graph expansion)
            top_k:  Number of top chunks to return

        Returns:
            Top-k chunks sorted by cross-encoder score (highest first).
            Each chunk gets a 'rerank_score' field added.
        """
        if not chunks:
            return []

        if self._model is None:
            # Fallback: return top_k by FAISS relevance_score
            return sorted(
                chunks,
                key=lambda c: c.get("relevance_score", 0),
                reverse=True,
            )[:top_k]

        # Build (query, passage) pairs for cross-encoder
        pairs = [(query, c.get("text", "")[:512]) for c in chunks]

        try:
            scores = self._model.predict(pairs, show_progress_bar=False)
            # Attach rerank score to each chunk
            for chunk, score in zip(chunks, scores):
                chunk["rerank_score"] = float(score)

            # Sort by rerank score descending
            reranked = sorted(chunks, key=lambda c: c.get("rerank_score", 0), reverse=True)
            return reranked[:top_k]

        except Exception as e:
            print(f"[Reranker] Reranking failed ({e}) — using FAISS order.")
            return sorted(
                chunks,
                key=lambda c: c.get("relevance_score", 0),
                reverse=True,
            )[:top_k]

    @property
    def available(self) -> bool:
        return self._model is not None
