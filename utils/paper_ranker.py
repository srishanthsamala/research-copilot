# ============================================================
# paper_ranker.py — Relevance-first ranking (Module 1 upgrade)
# Primary: semantic similarity to query (cosine score from FAISS)
# Secondary: citation count + recency + source credibility
# ============================================================
from typing import List
import numpy as np


def rank_papers(
    papers: List[dict],
    query_vector: List[float] = None,
    embedder=None,
    boost_recent: bool = True,
) -> List[dict]:
    """
    Rank papers using a composite score:
      40% Semantic relevance (if query_vector provided)
      40% Citation count (normalized)
      10% Recency (papers after 2018 get a bonus)
      10% Source credibility (IEEE/Springer slight boost)

    Args:
        papers:       List of paper dicts
        query_vector: Query embedding for semantic similarity (optional)
        embedder:     Embedder instance to embed abstracts (optional)
        boost_recent: Small bonus for recent papers

    Returns:
        Sorted list of papers (highest ranked first)
    """
    if not papers:
        return []

    # Find max citation count for normalization
    max_citations = max((p.get("citation_count", 0) or 0 for p in papers), default=1)
    if max_citations == 0:
        max_citations = 1

    # Pre-embed abstracts for semantic ranking if query vector provided
    abstract_vectors = {}
    if query_vector is not None and embedder is not None:
        try:
            abstracts = [p.get("abstract", p.get("title", ""))[:500] for p in papers]
            vecs = embedder.embed_texts(abstracts)
            for i, paper in enumerate(papers):
                abstract_vectors[id(paper)] = vecs[i]
        except Exception:
            pass  # Fall back to citation-only ranking

    query_arr = np.array(query_vector) if query_vector is not None else None

    scored = []
    for paper in papers:
        citations      = paper.get("citation_count", 0) or 0
        citation_score = citations / max_citations

        # Semantic similarity score (0–1)
        semantic_score = 0.0
        if query_arr is not None and id(paper) in abstract_vectors:
            paper_vec = np.array(abstract_vectors[id(paper)])
            denom = np.linalg.norm(query_arr) * np.linalg.norm(paper_vec)
            if denom > 0:
                semantic_score = float(np.dot(query_arr, paper_vec) / denom)
                semantic_score = max(0.0, semantic_score)  # Clamp negative

        # Recency bonus
        recency_bonus = 0.0
        if boost_recent:
            try:
                year = int(str(paper.get("year", "2000"))[:4])
                if year >= 2023:
                    recency_bonus = 0.12
                elif year >= 2021:
                    recency_bonus = 0.08
                elif year >= 2019:
                    recency_bonus = 0.04
            except (ValueError, TypeError):
                pass

        # Source credibility bonus
        source_bonus = 0.0
        source = paper.get("source", "")
        if source in ("IEEE", "Springer"):
            source_bonus = 0.06
        elif source in ("Semantic Scholar", "PubMed"):
            source_bonus = 0.03

        # Composite score
        if query_arr is not None and abstract_vectors:
            # Semantic ranking enabled
            score = (
                semantic_score  * 0.40 +
                citation_score  * 0.40 +
                recency_bonus        +
                source_bonus
            )
        else:
            # Citation-only ranking (fallback)
            score = citation_score * 0.80 + recency_bonus + source_bonus

        scored.append((score, paper))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored]


def filter_by_min_citations(papers: List[dict], min_count: int = 0) -> List[dict]:
    """Filter papers below a minimum citation threshold."""
    if min_count <= 0:
        return papers
    return [p for p in papers if (p.get("citation_count", 0) or 0) >= min_count]


def get_top_papers(papers: List[dict], n: int = 10) -> List[dict]:
    """Return the top N papers by composite score (citation-only fallback)."""
    ranked = rank_papers(papers)
    return ranked[:n]
