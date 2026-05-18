# ============================================================
# embedder.py — HuggingFace embedder with Semantic Chunking
# Module 2 upgrade: uses SemanticChunker instead of fixed splits
# ============================================================
import re
from typing import List
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP
from embeddings.semantic_chunker import SemanticChunker


class Embedder:
    """
    Handles text chunking and embedding generation.
    Uses local HuggingFace model — no API key or cost.
    Semantic chunking splits at meaning boundaries, not character counts.
    """

    def __init__(self):
        print(f"[Embedder] Loading model: {EMBEDDING_MODEL}")
        self.model           = SentenceTransformer(EMBEDDING_MODEL)
        self.semantic_chunker = SemanticChunker(
            model=self.model,
            similarity_threshold=0.45,
            max_chunk_chars=1200,
            min_chunk_chars=100,
        )
        print("[Embedder] Model loaded with semantic chunking enabled.")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of text strings."""
        if not texts:
            return []
        embeddings = self.model.encode(
            texts, show_progress_bar=False, normalize_embeddings=True
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """Generate a single embedding for a query string."""
        embedding = self.model.encode([query], normalize_embeddings=True)
        return embedding[0].tolist()

    def chunk_text(self, text: str,
                   chunk_size: int = CHUNK_SIZE,
                   overlap: int = CHUNK_OVERLAP) -> List[str]:
        """
        Semantically chunk text (Module 2).
        Falls back to sentence-boundary splitting if semantic chunker fails.
        """
        # Try semantic chunking first
        chunks = self.semantic_chunker.chunk(text)
        if chunks:
            return chunks

        # Fallback: sentence-boundary fixed-size chunking
        return self._fixed_chunk(text, chunk_size, overlap)

    @staticmethod
    def _fixed_chunk(text: str, chunk_size: int, overlap: int) -> List[str]:
        """Fallback fixed-size chunking with sentence awareness."""
        if not text or not text.strip():
            return []
        text      = re.sub(r"\s+", " ", text).strip()
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks    = []
        current   = ""

        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= chunk_size:
                current += (" " if current else "") + sentence
            else:
                if current:
                    chunks.append(current.strip())
                if chunks and overlap > 0:
                    overlap_text = current[-overlap:] if len(current) > overlap else current
                    current = overlap_text + " " + sentence
                else:
                    current = sentence

        if current.strip():
            chunks.append(current.strip())

        return [c for c in chunks if len(c) > 50]

    def chunk_paper(self, paper: dict) -> List[dict]:
        """
        Chunk a paper into retrievable semantic segments.
        Each chunk carries full paper metadata for citation mapping.
        """
        text_parts = []
        if paper.get("abstract"):
            text_parts.append(f"Abstract: {paper['abstract']}")
        if paper.get("full_text") and paper["full_text"] != paper.get("abstract"):
            text_parts.append(paper["full_text"])

        combined = " ".join(text_parts)
        if not combined.strip():
            return []

        raw_chunks  = self.chunk_text(combined)
        chunk_dicts = []

        for i, chunk_text in enumerate(raw_chunks):
            chunk_dicts.append({
                "chunk_id":       f"{paper.get('doi', paper.get('title',''))[:40]}_{i}",
                "text":           chunk_text,
                "paper_title":    paper.get("title", ""),
                "paper_authors":  paper.get("authors", []),
                "paper_year":     paper.get("year", "N/A"),
                "paper_source":   paper.get("source", ""),
                "paper_url":      paper.get("url", ""),
                "paper_doi":      paper.get("doi", ""),
                "citation_count": paper.get("citation_count", 0),
            })

        return chunk_dicts
