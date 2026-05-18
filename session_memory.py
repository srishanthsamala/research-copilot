# ============================================================
# session_memory.py — Module 4: Persistent Session Context
#
# Tracks per-session:
#   • Fetched topics → avoids re-fetching the same papers
#   • Conversation history → enables coherent follow-up Q&A
#   • Indexed papers → persists FAISS index across queries
#     on the same topic (only re-fetches on new topic)
#   • Semantic similarity check: determines if new query
#     is a follow-up to previous one or a new topic
# ============================================================
from __future__ import annotations
import re
import time
from typing import Dict, List, Optional
import numpy as np


class SessionMemory:
    """
    Manages session state for persistent, context-aware research.

    Key behaviors:
    - Same topic:  reuse existing FAISS index → skip re-fetching
    - New topic:   clear index and fetch fresh papers
    - Follow-up:   prepend prior conversation turns to LLM context
    """

    def __init__(self, similarity_threshold: float = 0.72):
        """
        Args:
            similarity_threshold: Cosine sim above this = same topic (no re-fetch)
        """
        self.threshold          = similarity_threshold
        self.conversation_history: List[Dict] = []
        self.current_topic:        str        = ""
        self.current_topic_vec:    Optional[list] = None
        self.fetched_topics:       List[str]  = []   # History of queried topics
        self.papers_indexed:       int        = 0
        self.session_start:        float      = time.time()
        self._embedder             = None   # Lazy: set on first use

    # ──────────────────────────────────────────────────────────
    # Topic management
    # ──────────────────────────────────────────────────────────

    def is_same_topic(self, new_query: str, embedder) -> bool:
        """
        Check if new_query is semantically similar to current topic.
        If yes → skip paper fetching (reuse index).
        If no  → clear index and fetch fresh papers.
        """
        if not self.current_topic or self.current_topic_vec is None:
            return False

        new_vec = embedder.embed_query(new_query)
        sim     = self._cosine(self.current_topic_vec, new_vec)
        print(f"[SessionMemory] Topic similarity: {sim:.3f} (threshold: {self.threshold})")
        return sim >= self.threshold

    def update_topic(self, query: str, embedder):
        """Register a new topic after clearing the index."""
        self.current_topic     = query
        self.current_topic_vec = embedder.embed_query(query)
        self.fetched_topics.append(query)

    # ──────────────────────────────────────────────────────────
    # Conversation history management
    # ──────────────────────────────────────────────────────────

    def add_turn(self, user_msg: str, assistant_msg: str):
        """Record a conversation turn (user query + AI answer)."""
        self.conversation_history.append({"role": "user",      "content": user_msg})
        self.conversation_history.append({"role": "assistant",  "content": assistant_msg})

    def get_context_window(self, max_turns: int = 6) -> List[Dict]:
        """Return last N turns for LLM context injection."""
        # Take the last max_turns messages (pairs of user+assistant)
        n = max_turns * 2
        return self.conversation_history[-n:] if len(self.conversation_history) > n \
               else self.conversation_history[:]

    def clear_conversation(self):
        """Reset conversation but keep current topic index."""
        self.conversation_history = []

    def full_reset(self):
        """Complete reset: conversation + topic + indexed papers."""
        self.conversation_history  = []
        self.current_topic         = ""
        self.current_topic_vec     = None
        self.fetched_topics        = []
        self.papers_indexed        = 0

    # ──────────────────────────────────────────────────────────
    # Stats
    # ──────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "session_age_min":    round((time.time() - self.session_start) / 60, 1),
            "turns":              len(self.conversation_history) // 2,
            "topics_queried":     len(self.fetched_topics),
            "current_topic":      self.current_topic[:60] if self.current_topic else "None",
            "papers_indexed":     self.papers_indexed,
        }

    # ──────────────────────────────────────────────────────────
    # Private
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _cosine(vec_a: list, vec_b: list) -> float:
        a = np.array(vec_a)
        b = np.array(vec_b)
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)
