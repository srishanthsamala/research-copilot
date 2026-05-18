# ============================================================
# semantic_chunker.py — Module 2: Semantic Chunking
# Splits text at semantic breakpoints (cosine similarity drop)
# instead of fixed character counts, preserving meaning.
# ============================================================
import re
import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer


class SemanticChunker:
    """
    Semantic chunking: embeds sentences, finds cosine similarity drops
    between adjacent sentences, and splits at those breakpoints.

    This produces coherent chunks that respect topic boundaries,
    unlike fixed character-length splits that cut mid-concept.
    """

    def __init__(self, model: SentenceTransformer,
                 similarity_threshold: float = 0.45,
                 max_chunk_chars: int = 1200,
                 min_chunk_chars: int = 100):
        """
        Args:
            model:                Shared SentenceTransformer instance (no reload)
            similarity_threshold: Below this cosine sim → split point
            max_chunk_chars:      Hard cap on chunk size before forced split
            min_chunk_chars:      Minimum viable chunk size
        """
        self.model               = model
        self.threshold           = similarity_threshold
        self.max_chunk_chars     = max_chunk_chars
        self.min_chunk_chars     = min_chunk_chars

    def chunk(self, text: str) -> List[str]:
        """
        Chunk text semantically.

        1. Split text into sentences
        2. Embed each sentence
        3. Compute cosine similarity between adjacent pairs
        4. Split where similarity < threshold OR chunk > max_chars
        5. Merge tiny fragments with neighbours

        Returns list of coherent chunk strings.
        """
        if not text or not text.strip():
            return []

        sentences = self._split_sentences(text)
        if len(sentences) <= 2:
            # Too short for semantic splitting — return as one chunk
            return [text.strip()] if len(text) >= self.min_chunk_chars else []

        # Embed all sentences (batch for efficiency)
        try:
            embeddings = self.model.encode(
                sentences, show_progress_bar=False, normalize_embeddings=True
            )
        except Exception:
            # Fallback to simple splitting if embedding fails
            return self._simple_chunk(text)

        # Compute pairwise cosine similarities (normalized → dot product = cosine)
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = float(np.dot(embeddings[i], embeddings[i + 1]))
            similarities.append(sim)

        # Identify split points
        chunks      = []
        current     = [sentences[0]]
        current_len = len(sentences[0])

        for i, sim in enumerate(similarities):
            next_sentence = sentences[i + 1]
            next_len      = len(next_sentence)

            # Split if: semantic break OR chunk would exceed max size
            should_split = (
                sim < self.threshold
                or (current_len + next_len) > self.max_chunk_chars
            )

            if should_split and current_len >= self.min_chunk_chars:
                chunks.append(" ".join(current))
                current     = [next_sentence]
                current_len = next_len
            else:
                current.append(next_sentence)
                current_len += next_len + 1

        # Flush last chunk
        if current:
            remaining = " ".join(current)
            if len(remaining) >= self.min_chunk_chars:
                chunks.append(remaining)
            elif chunks:
                # Merge tiny tail with previous chunk
                chunks[-1] += " " + remaining

        return [c.strip() for c in chunks if c.strip()]

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split text into sentences, cleaning whitespace."""
        text = re.sub(r"\s+", " ", text).strip()
        # Split on sentence-ending punctuation followed by space + capital
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        # Filter empty and very short fragments
        return [s.strip() for s in sentences if len(s.strip()) > 20]

    def _simple_chunk(self, text: str, size: int = 900) -> List[str]:
        """Fallback: simple fixed-size chunking."""
        text   = re.sub(r"\s+", " ", text).strip()
        chunks = []
        for i in range(0, len(text), size - 100):
            chunk = text[i:i + size]
            if len(chunk) >= self.min_chunk_chars:
                chunks.append(chunk)
        return chunks
