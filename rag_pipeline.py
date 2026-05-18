# ============================================================
# rag_pipeline.py — Scholar Graphite v2: Proper RAG Pipeline
#
# Proper RAG flow:
#   1.  User query → LLM Query Expander (semantic understanding)
#   2.  Session check: same topic → skip fetch, reuse index
#   3.  Parallel fetch from 6 academic APIs (expanded query)
#   4.  Enrich citation counts via Semantic Scholar
#   5.  Unpaywall OA fallback for paywalled papers
#   6.  Semantic relevance-first ranking (cosine + citations)
#   7.  Semantic chunking (meaning-boundary splits)
#   8.  Embed all chunks → FAISS index (broad retrieval)
#   9.  Build GraphRAG: LLM extracts entities + relationships
#  10.  FAISS retrieves top-30 candidates (broad recall)
#  11.  GraphRAG multi-hop expansion (conceptually connected papers)
#  12.  Cross-encoder reranks all candidates → top-8 (precision)
#  13.  LLM generates explanation-first grounded answer
#  14.  Honest guardrail: explicit "insufficient data" response
#  15.  Session memory updated (conversation history + topic)
# ============================================================
import concurrent.futures
import threading
from typing import Dict, List, Optional, Tuple

from config import MAX_PAPERS_PER_SOURCE, TOP_K_RESULTS
from fetchers import (
    fetch_arxiv, fetch_ieee, fetch_springer,
    fetch_semantic_scholar, fetch_pubmed, fetch_crossref,
)
from fetchers.semantic_scholar_fetcher import enrich_citation_counts
from fetchers.paywall_bypass import get_open_access_pdf
from embeddings import Embedder
from vector_store import FAISSVectorStore
from llm import GroqLLM
from utils.paper_ranker import rank_papers
from utils.citation_mapper import CitationMapper
from query_expander import QueryExpander
from graph_rag import GraphRAG
from reranker import CrossEncoderReranker
from session_memory import SessionMemory


class RAGPipeline:
    """
    Scholar Graphite v2 — Full RAG pipeline with:
      - LLM query understanding (not keyword extraction)
      - GraphRAG with LLM entity extraction
      - Cross-encoder reranking (precision retrieval)
      - Explanation-first generation (no dry summaries)
      - Honest guardrails (no hallucination)
      - Session memory (no redundant fetches)
    """

    # ── Stop words for keyword filter ────────────────────────
    STOP_WORDS = {
        "what","are","is","the","a","an","of","in","to","for","on","at","by",
        "from","with","about","as","into","through","during","before","after",
        "above","below","between","out","off","over","under","again","further",
        "then","once","here","there","when","where","why","how","all","both",
        "each","few","more","most","other","some","such","no","nor","not",
        "only","own","same","so","than","too","very","can","will","just",
        "should","now","tell","me","us","give","show","please","latest",
        "recent","new","old","any","its","it","this","that","these","those",
        "i","you","he","she","we","they","do","did","does","has","have","had",
        "be","been","being","am","was","were","would","could","might","may",
        "shall","summarize","explain","describe","compare","review","analyze",
        "find","get","make","take","use","using","used","based","related",
        "paper","papers","research","study","studies","article","articles",
        "also","even","still","yet","well","often","many","much","little",
        "your","our","their","my","his","her","and","or","but","if","while",
    }

    def __init__(self):
        print("[RAGPipeline] Initialising all modules...")
        self.embedder        = Embedder()
        self.vector_store    = FAISSVectorStore(dimension=384)
        self.llm             = GroqLLM()
        self.citation_mapper = CitationMapper()
        self.query_expander  = QueryExpander()
        self.graph           = GraphRAG()
        self.reranker        = CrossEncoderReranker()
        self.session         = SessionMemory()
        self.fetch_counts    : Dict[str, int] = {}
        self._all_papers     : List[dict]     = []
        self._lock           = threading.Lock()
        print(f"[RAGPipeline] Ready. "
              f"Reranker: {'✓' if self.reranker.available else '✗ (FAISS order)'}")

    # ──────────────────────────────────────────────────────────
    # Public: Main query
    # ──────────────────────────────────────────────────────────

    def query(
        self,
        user_query: str,
        conversation_history: list = None,
        top_k: int = TOP_K_RESULTS,
    ) -> Tuple[str, List[Dict], List[Dict]]:
        """
        Full RAG query — understanding → retrieval → rerank → generate.
        """
        print(f"\n[RAGPipeline] Query: '{user_query}'")

        # Step 1: Session check — same topic → reuse index
        same_topic = self.session.is_same_topic(user_query, self.embedder)

        if not same_topic:
            # Step 2: LLM query expansion — semantic understanding
            expansion = self.query_expander.expand(user_query)
            print(f"[QueryExpander] '{expansion['primary_query']}' | "
                  f"domain: {expansion.get('domain','?')}")

            # Steps 3–9: Fetch → enrich → rank → chunk → embed → FAISS → GraphRAG
            self._ingest(user_query, expansion)
            self.session.update_topic(user_query, self.embedder)
        else:
            print("[SessionMemory] Same topic — reusing existing index.")

        if self.vector_store.get_chunk_count() == 0:
            return (
                "⚠️ No papers could be fetched for your query. "
                "Please verify your GROQ_API_KEY in config.py and ensure "
                "you have an internet connection.",
                [], []
            )

        # Step 10: FAISS broad retrieval (top 30 for reranker input)
        query_embedding  = self.embedder.embed_query(user_query)
        faiss_chunks     = self.vector_store.retrieve(query_embedding, top_k=30)

        # Step 11: GraphRAG multi-hop expansion
        graph_chunks = self.graph.get_graph_expanded_chunks(
            seed_chunks=faiss_chunks,
            user_query=user_query,
            max_hops=2,
            max_extra=10,
        )
        # Merge without duplicates
        seen_ids    = {c.get("chunk_id") for c in faiss_chunks}
        all_candidates = list(faiss_chunks)
        for gc in graph_chunks:
            if gc.get("chunk_id") not in seen_ids:
                all_candidates.append(gc)
                seen_ids.add(gc.get("chunk_id"))

        print(f"[RAGPipeline] Candidates: {len(faiss_chunks)} FAISS + "
              f"{len(graph_chunks)} graph = {len(all_candidates)} total")

        # Step 12: Cross-encoder reranking → top-8 high-precision chunks
        top_chunks = self.reranker.rerank(
            query=user_query,
            chunks=all_candidates,
            top_k=top_k,
        )
        print(f"[Reranker] Reranked to top {len(top_chunks)} chunks")

        # Step 13: Build session context window
        context_history = self.session.get_context_window(max_turns=6)

        # Step 14: Generate explanation-first grounded answer
        answer = self.llm.generate_rag_answer(
            query=user_query,
            context_chunks=top_chunks,
            conversation_history=context_history,
        )

        # Step 15: Map citations + update session
        cited_papers = self.citation_mapper.extract_cited_papers(top_chunks)
        self.session.add_turn(user_query, answer)
        self.session.papers_indexed = self.vector_store.get_paper_count()

        return answer, top_chunks, cited_papers

    # ──────────────────────────────────────────────────────────
    # Public: Paper comparison
    # ──────────────────────────────────────────────────────────

    def compare_papers(self, paper_titles: List[str]) -> str:
        all_papers = self.vector_store.get_all_papers()
        selected   = [p for p in all_papers if p["title"] in paper_titles]
        if len(selected) < 2:
            return (
                "⚠️ Select at least 2 papers from the library tab. "
                "Papers must be indexed in the current session."
            )
        return self.llm.generate_comparison(selected)

    # ──────────────────────────────────────────────────────────
    # Public: PDF upload (Module 5) — full RAG, not raw LLM
    # ──────────────────────────────────────────────────────────

    def review_paper(self, paper_text: str, question: str = "") -> str:
        if not paper_text.strip():
            return "Could not extract text from the uploaded paper."

        synthetic = {
            "title": "Uploaded Paper", "abstract": "", "full_text": paper_text,
            "authors": ["[Uploaded]"], "year": "2024", "source": "Upload",
            "citation_count": 0, "doi": "", "url": "",
        }

        # Semantic chunk the PDF
        chunks = self.embedder.chunk_paper(synthetic)
        if not chunks:
            return "Could not extract meaningful text segments from the paper."

        # Embed into a temporary FAISS store
        texts      = [c["text"] for c in chunks]
        embeddings = self.embedder.embed_texts(texts)
        pdf_store  = FAISSVectorStore(dimension=384)
        pdf_store.add_chunks(chunks, embeddings)

        # Retrieve relevant chunks
        q = question or "Explain the key contributions, methodology, and findings of this paper."
        q_vec  = self.embedder.embed_query(q)
        hits   = pdf_store.retrieve(q_vec, top_k=30)

        # Rerank
        top    = self.reranker.rerank(q, hits, top_k=8)

        # Generate via RAG (grounded, not raw LLM)
        return self.llm.generate_rag_answer(
            query=q,
            context_chunks=top,
            conversation_history=None,
        )

    # ──────────────────────────────────────────────────────────
    # Public: Session management
    # ──────────────────────────────────────────────────────────

    def new_chat(self):
        self.session.clear_conversation()

    def clear_all(self):
        self.vector_store.clear()
        self.graph.clear()
        self.citation_mapper.clear()
        self.fetch_counts = {}
        self._all_papers  = []
        self.session.full_reset()

    def get_fetch_counts(self)  -> Dict[str, int]: return dict(self.fetch_counts)
    def get_all_papers(self)    -> List[Dict]:      return self.vector_store.get_all_papers()
    def get_session_stats(self) -> dict:
        s = self.session.get_stats()
        s["graph"] = self.graph.get_stats()
        s["reranker_active"] = self.reranker.available
        return s

    # ──────────────────────────────────────────────────────────
    # Private: Full ingestion pipeline
    # ──────────────────────────────────────────────────────────

    def _ingest(self, user_query: str, expansion: dict):
        """
        Steps 3–9: fetch → enrich → deduplicate → rank → chunk → embed → index → GraphRAG.
        """
        self.vector_store.clear()
        self.graph.clear()
        self.citation_mapper.clear()
        self.fetch_counts = {}
        self._all_papers  = []

        primary_query = expansion.get("primary_query", user_query)

        # ── Step 3: Parallel fetch from all 6 sources ────────
        fetchers = {
            "arXiv":            fetch_arxiv,
            "IEEE":             fetch_ieee,
            "Springer":         fetch_springer,
            "Semantic Scholar": fetch_semantic_scholar,
            "PubMed":           fetch_pubmed,
            "CrossRef":         fetch_crossref,
        }
        all_papers = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            futures = {ex.submit(fn, primary_query): src for src, fn in fetchers.items()}
            for fut in concurrent.futures.as_completed(futures):
                src = futures[fut]
                try:
                    papers = fut.result()
                    with self._lock:
                        self.fetch_counts[src] = len(papers)
                        all_papers.extend(papers)
                    print(f"  [{src}] {len(papers)} papers")
                except Exception as e:
                    print(f"  [{src}] error: {e}")
                    self.fetch_counts[src] = 0

        if not all_papers:
            print("[RAGPipeline] No papers fetched.")
            return

        # ── Step 4: Enrich citation counts ───────────────────
        all_papers = enrich_citation_counts(all_papers)

        # ── Step 5: Unpaywall OA fallback ────────────────────
        self._enrich_oa(all_papers)

        # ── Deduplicate + relevance filter ───────────────────
        query_kws = [
            kw for kw in primary_query.lower().split()
            if kw not in self.STOP_WORDS and len(kw) > 3
        ]
        seen, unique = set(), []
        for p in all_papers:
            key = p.get("title","").lower().strip()
            if not key or key in seen:
                continue
            seen.add(key)
            if not query_kws:
                unique.append(p)
                continue
            combined = (p.get("title","") + " " + p.get("abstract","")).lower()
            if any(kw in combined for kw in query_kws):
                unique.append(p)

        # ── Step 6: Semantic relevance-first ranking ──────────
        query_vec     = self.embedder.embed_query(user_query)
        ranked_papers = rank_papers(unique, query_vector=query_vec, embedder=self.embedder)
        print(f"[RAGPipeline] {len(ranked_papers)} papers after dedup + ranking")
        self._all_papers = ranked_papers

        # ── Steps 7–8: Semantic chunk + embed + FAISS index ──
        all_chunks  = []
        chunks_map  = {}   # paper_id → chunks (for GraphRAG)
        for paper in ranked_papers:
            chunks = self.embedder.chunk_paper(paper)
            pid    = self.graph._pid(paper)
            chunks_map[pid] = chunks
            all_chunks.extend(chunks)
            self.citation_mapper.register_paper(paper)

        if not all_chunks:
            return

        print(f"[RAGPipeline] Embedding {len(all_chunks)} semantic chunks...")
        texts      = [c["text"] for c in all_chunks]
        embeddings = self.embedder.embed_texts(texts)
        self.vector_store.add_chunks(all_chunks, embeddings)

        # ── Step 9: Build GraphRAG knowledge graph ────────────
        print("[GraphRAG] Extracting entities and building knowledge graph...")
        self.graph.build_graph(ranked_papers, chunks_map)
        g = self.graph.get_stats()
        print(f"[GraphRAG] {g['entities']} entities | {g['edges']} edges | "
              f"{g['papers']} papers")

    def _enrich_oa(self, papers: List[dict]):
        """Try Unpaywall for papers with DOI but no full text."""
        n = 0
        for p in papers:
            if not p.get("full_text") and p.get("doi"):
                url = get_open_access_pdf(doi=p["doi"], title=p.get("title",""))
                if url:
                    p["oa_pdf_url"] = url
                    n += 1
        if n:
            print(f"[Unpaywall] {n} open-access versions found")
