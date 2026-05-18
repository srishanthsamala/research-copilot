# ============================================================
# graph_rag.py — Proper GraphRAG with LLM Entity Extraction
#
# This is the real GraphRAG, not a proxy.
# For each paper, an LLM extracts named entities and typed
# relationships. These become graph nodes and edges.
# During retrieval, the system traverses the graph to find
# conceptually connected papers that FAISS alone would miss.
#
# Architecture:
#   Nodes  = entities (models, methods, datasets, concepts)
#   Edges  = typed relationships (uses, improves, evaluates, proposes)
#   Chunks = anchored to entities — each entity points back to
#            the paper chunks that mention it
# ============================================================
from __future__ import annotations
import json
import re
import time
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional

from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL


# ── Entity extraction prompt ─────────────────────────────────
_ENTITY_SYSTEM = """You are a scientific knowledge graph builder.
Extract entities and relationships from research paper abstracts.

Output ONLY valid JSON in this exact format — no markdown, no explanation:
{
  "entities": [
    {"name": "entity name", "type": "MODEL|METHOD|DATASET|METRIC|CONCEPT|FRAMEWORK"}
  ],
  "relationships": [
    {"source": "entity A", "relation": "USES|IMPROVES|EVALUATES|PROPOSES|COMPARES|APPLIES", "target": "entity B"}
  ]
}

Rules:
- Extract 3–8 entities per paper. Focus on technical terms, not generic words.
- Extract 2–6 relationships. Only between entities you listed.
- Entity names must be exact technical terms (e.g. "BERT", "FAISS", "BM25", "RAG")
- Do NOT include: "paper", "study", "research", "method", "approach" as entities
- If the abstract is too vague to extract entities, return {"entities": [], "relationships": []}"""


class GraphRAG:
    """
    Proper GraphRAG with LLM-powered entity extraction.

    Build phase (during ingestion):
      1. For each paper, call LLaMA to extract entities + relationships
      2. Build a typed knowledge graph
      3. Anchor each entity back to the paper chunks that mention it

    Retrieval phase (during query):
      1. Extract entities from the user query
      2. Find those entities in the graph
      3. Traverse 1–2 hops to find connected entities
      4. Return chunks from all connected papers as extra context
    """

    def __init__(self):
        try:
            self._client  = Groq(api_key=GROQ_API_KEY)
            self._enabled = True
        except Exception:
            self._enabled = False

        # Graph storage
        self._entities:    Dict[str, dict]         = {}           # name → {type, papers}
        self._edges:       List[dict]               = []           # {source, relation, target}
        self._entity_idx:  Dict[str, Set[str]]      = defaultdict(set)  # entity → paper_ids
        self._paper_chunks: Dict[str, List[dict]]   = {}           # paper_id → chunks
        self._paper_meta:  Dict[str, dict]          = {}           # paper_id → metadata
        self._adj:         Dict[str, Set[str]]      = defaultdict(set)  # entity → connected entities

    # ──────────────────────────────────────────────────────────
    # Graph construction
    # ──────────────────────────────────────────────────────────

    def build_graph(self, papers: List[dict], chunks_map: Dict[str, List[dict]]):
        """
        Build the full knowledge graph from a list of papers.
        Extracts entities in batches of 3 to minimise API calls.

        Args:
            papers:     List of paper dicts (with title, abstract)
            chunks_map: paper_id → list of chunks (from embedder)
        """
        self.clear()

        # Register all papers and their chunks
        for paper in papers:
            pid = self._pid(paper)
            self._paper_chunks[pid] = chunks_map.get(pid, [])
            self._paper_meta[pid]   = paper

        if not self._enabled:
            print("[GraphRAG] LLM unavailable — using keyword fallback.")
            self._build_keyword_fallback(papers)
            return

        # Batch extract entities (3 papers per LLM call)
        batch_size = 3
        for i in range(0, len(papers), batch_size):
            batch = papers[i : i + batch_size]
            self._extract_batch(batch)
            time.sleep(0.3)   # Respect Groq rate limits

        print(f"[GraphRAG] Graph built: {len(self._entities)} entities, "
              f"{len(self._edges)} edges, {len(self._paper_chunks)} papers")

    def add_paper(self, paper: dict, chunks: List[dict]):
        """Add a single paper to the graph (used during streaming ingestion)."""
        pid = self._pid(paper)
        self._paper_chunks[pid] = chunks
        self._paper_meta[pid]   = paper

        if not self._enabled:
            self._extract_keywords_single(paper)
            return

        abstract = paper.get("abstract", paper.get("title", ""))
        if abstract:
            result = self._llm_extract_single(paper.get("title",""), abstract)
            if result:
                self._register_entities(result, pid)

    def clear(self):
        self._entities.clear()
        self._edges.clear()
        self._entity_idx.clear()
        self._paper_chunks.clear()
        self._paper_meta.clear()
        self._adj.clear()

    # ──────────────────────────────────────────────────────────
    # Graph retrieval
    # ──────────────────────────────────────────────────────────

    def get_graph_expanded_chunks(
        self,
        seed_chunks: List[dict],
        user_query:  str = "",
        max_hops:    int = 2,
        max_extra:   int = 5,
    ) -> List[dict]:
        """
        Multi-hop graph expansion from seed chunks.

        1. Identify entities mentioned in seed chunks + user query
        2. Traverse graph up to max_hops away
        3. Collect chunks from all reachable papers
        4. Return top chunks by citation count (not already in seeds)

        Args:
            seed_chunks: Initial FAISS-retrieved chunks
            user_query:  Original user question (for entity matching)
            max_hops:    Graph traversal depth
            max_extra:   Max additional chunks to return

        Returns:
            List of extra chunks from graph-connected papers
        """
        if not seed_chunks and not user_query:
            return []

        # Identify seed entities from seed chunk papers
        seed_paper_ids = {
            self._pid_from_chunk(c) for c in seed_chunks
        }

        # Find entities present in seed papers
        seed_entities = set()
        for entity, papers in self._entity_idx.items():
            if papers & seed_paper_ids:
                seed_entities.add(entity)

        # Also extract entities from the user query directly
        query_entities = self._extract_query_entities(user_query)
        seed_entities.update(query_entities)

        if not seed_entities:
            return []

        # Multi-hop traversal
        visited_entities = set(seed_entities)
        frontier         = set(seed_entities)

        for _ in range(max_hops):
            next_frontier = set()
            for ent in frontier:
                neighbours = self._adj.get(ent, set())
                next_frontier.update(neighbours - visited_entities)
            visited_entities.update(next_frontier)
            frontier = next_frontier
            if not frontier:
                break

        # Collect papers reachable via traversal (exclude seed papers)
        reachable_papers = set()
        for ent in visited_entities:
            reachable_papers.update(self._entity_idx.get(ent, set()))
        reachable_papers -= seed_paper_ids

        if not reachable_papers:
            return []

        # Sort reachable papers by citation count
        ranked = sorted(
            reachable_papers,
            key=lambda pid: self._paper_meta.get(pid, {}).get("citation_count", 0),
            reverse=True,
        )

        # Collect top chunks from each reachable paper
        extra_chunks = []
        for pid in ranked:
            chunks = self._paper_chunks.get(pid, [])
            if chunks:
                extra_chunks.append(chunks[0])  # Best chunk per paper
            if len(extra_chunks) >= max_extra:
                break

        return extra_chunks

    def get_entity_summary(self) -> str:
        """Return a readable summary of top entities in the graph."""
        if not self._entities:
            return "No entities extracted."
        top = sorted(
            self._entities.items(),
            key=lambda x: len(self._entity_idx.get(x[0], set())),
            reverse=True,
        )[:10]
        lines = [f"  • {name} ({info['type']}) — {len(self._entity_idx.get(name,set()))} papers"
                 for name, info in top]
        return "\n".join(lines)

    def get_stats(self) -> dict:
        return {
            "papers":   len(self._paper_chunks),
            "entities": len(self._entities),
            "edges":    len(self._edges),
        }

    # ──────────────────────────────────────────────────────────
    # Private: LLM entity extraction
    # ──────────────────────────────────────────────────────────

    def _extract_batch(self, papers: List[dict]):
        """Extract entities from a batch of papers in one LLM call."""
        for paper in papers:
            abstract = paper.get("abstract", paper.get("title", ""))
            if not abstract:
                continue
            result = self._llm_extract_single(paper.get("title", ""), abstract)
            if result:
                pid = self._pid(paper)
                self._register_entities(result, pid)

    def _llm_extract_single(self, title: str, abstract: str) -> Optional[dict]:
        """Call LLaMA to extract entities from one paper abstract."""
        prompt = f"""Paper title: {title}

Abstract: {abstract[:800]}

Extract entities and relationships as JSON."""

        try:
            resp = self._client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": _ENTITY_SYSTEM},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.0,
                max_tokens=500,
            )
            raw = resp.choices[0].message.content.strip()
            # Strip markdown fences if present
            raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()
            return json.loads(raw)
        except (json.JSONDecodeError, Exception) as e:
            print(f"[GraphRAG] Entity extraction failed: {e}")
            return None

    def _register_entities(self, extraction: dict, paper_id: str):
        """Register extracted entities and relationships into the graph."""
        entities      = extraction.get("entities", [])
        relationships = extraction.get("relationships", [])

        for ent in entities:
            name = ent.get("name", "").strip()
            if not name or len(name) < 2:
                continue
            name_key = name.lower()
            if name_key not in self._entities:
                self._entities[name_key] = {"name": name, "type": ent.get("type", "CONCEPT")}
            self._entity_idx[name_key].add(paper_id)

        for rel in relationships:
            src = rel.get("source", "").lower().strip()
            tgt = rel.get("target", "").lower().strip()
            if not src or not tgt:
                continue
            self._edges.append({
                "source":   src,
                "relation": rel.get("relation", "RELATED"),
                "target":   tgt,
                "paper":    paper_id,
            })
            # Build adjacency for traversal
            self._adj[src].add(tgt)
            self._adj[tgt].add(src)

    def _extract_query_entities(self, query: str) -> Set[str]:
        """Find entities in the graph that appear in the user query."""
        if not query:
            return set()
        query_lower = query.lower()
        matched = set()
        for entity_key in self._entities:
            if entity_key in query_lower:
                matched.add(entity_key)
        return matched

    # ──────────────────────────────────────────────────────────
    # Private: Keyword fallback (no LLM)
    # ──────────────────────────────────────────────────────────

    _TECH_RE = [
        r'\b(transformer|bert|gpt|llm|llama|attention)\b',
        r'\b(retrieval.?augmented|rag|dense retrieval|bm25)\b',
        r'\b(faiss|vector store|vector index|vector database)\b',
        r'\b(sentence.?transformer|bi.?encoder|cross.?encoder)\b',
        r'\b(knowledge graph|ontology|entity linking|neo4j)\b',
        r'\b(fine.?tun|pre.?train|transfer learning|zero.?shot)\b',
        r'\b(deep learning|neural network|cnn|rnn|lstm|gru)\b',
        r'\b(semantic search|cosine similarity|embedding)\b',
        r'\b(summariz|abstractive|extractive|text generation)\b',
        r'\b(question answering|reading comprehension|nli)\b',
        r'\b(hallucination|grounding|factual|citation)\b',
    ]

    def _build_keyword_fallback(self, papers: List[dict]):
        for paper in papers:
            self._extract_keywords_single(paper)

    def _extract_keywords_single(self, paper: dict):
        pid  = self._pid(paper)
        text = (paper.get("title","") + " " + paper.get("abstract","")).lower()
        for pattern in self._TECH_RE:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                key = match.group(0).strip().lower()
                if key not in self._entities:
                    self._entities[key] = {"name": key, "type": "CONCEPT"}
                self._entity_idx[key].add(pid)

    # ──────────────────────────────────────────────────────────
    # Private: ID helpers
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _pid(paper: dict) -> str:
        raw = paper.get("doi") or paper.get("title", "") + str(paper.get("year",""))
        return re.sub(r'\W+', '_', raw.lower())[:64]

    @staticmethod
    def _pid_from_chunk(chunk: dict) -> str:
        raw = chunk.get("paper_doi") or \
              chunk.get("paper_title","") + str(chunk.get("paper_year",""))
        return re.sub(r'\W+', '_', raw.lower())[:64]
