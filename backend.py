# ============================================================
# backend.py — Scholar Graphite v2 FastAPI Server
# Run:  uvicorn backend:app --reload --port 8000
# ============================================================
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from rag_pipeline import RAGPipeline
from utils.pdf_parser import extract_pdf_text, extract_paper_metadata

# ── App ──────────────────────────────────────────────────────
app = FastAPI(
    title="Scholar Graphite v2 API",
    version="2.0.0",
    description=(
        "Enhanced RAG pipeline with semantic chunking, GraphRAG, "
        "query expansion, session memory, and honest guardrails."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        os.getenv("FRONTEND_ORIGIN", ""),
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pipeline singleton ────────────────────────────────────────
pipeline: Optional[RAGPipeline] = None


@app.on_event("startup")
async def startup():
    global pipeline
    print("🔧 Initialising Scholar Graphite v2 pipeline...")
    pipeline = RAGPipeline()
    print("✅ Pipeline ready — all 5 modules loaded.")


# ════════════════════════════════════════════════════════════════
# MODELS
# ════════════════════════════════════════════════════════════════

class QueryRequest(BaseModel):
    query: str
    top_k: int = 14


class CompareRequest(BaseModel):
    paper_titles: List[str]


# ════════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    return {
        "status":         "ok",
        "pipeline_ready": pipeline is not None,
        "version":        "2.0.0",
    }


@app.post("/api/query")
async def query_endpoint(req: QueryRequest):
    """
    Main RAG query endpoint.
    Module 1: query expansion + honest guardrails
    Module 2: GraphRAG multi-hop retrieval
    Module 4: session memory (same topic → no re-fetch)
    """
    global pipeline
    if not pipeline:
        raise HTTPException(503, "Pipeline not ready yet")
    try:
        # Pipeline now manages conversation history via SessionMemory (Module 4)
        answer, chunks, cited_papers = pipeline.query(
            user_query=req.query,
            top_k=req.top_k,
        )

        # Normalise cited_papers for frontend
        normalised = []
        for p in cited_papers:
            authors_raw = p.get("authors", [])
            if isinstance(authors_raw, list):
                auth_str = authors_raw[0] if authors_raw else "Unknown"
                if len(authors_raw) > 1:
                    auth_str += " et al."
            else:
                auth_str = str(authors_raw)
            normalised.append({
                "title":          p.get("title", "N/A"),
                "source":         p.get("source", ""),
                "authors":        auth_str,
                "year":           str(p.get("year", "N/A")),
                "doi":            p.get("doi", ""),
                "url":            p.get("url", p.get("oa_pdf_url", "#")),
                "citation_count": p.get("citation_count", 0),
                "oa_available":   bool(p.get("oa_pdf_url")),  # Module 3 flag
            })

        return {
            "answer":       answer,
            "cited_papers": normalised,
            "fetch_counts": pipeline.get_fetch_counts(),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, str(e))


@app.post("/api/compare")
async def compare_endpoint(req: CompareRequest):
    """
    Multi-stage paper comparison (Module 4).
    Stage 1: methodology extraction
    Stage 2: metric comparison table
    Stage 3: consensus + gap summary
    """
    if not pipeline:
        raise HTTPException(503, "Pipeline not ready yet")
    if len(req.paper_titles) < 2:
        raise HTTPException(400, "Need at least 2 papers to compare")
    try:
        result = pipeline.compare_papers(req.paper_titles)
        return {"result": result}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/papers")
async def papers_endpoint():
    """Return all papers fetched and indexed in this session."""
    if not pipeline:
        return {"papers": []}
    all_papers = pipeline.get_all_papers()
    out = []
    for p in all_papers:
        authors_raw = p.get("authors", [])
        if isinstance(authors_raw, list):
            auth_str = ", ".join(authors_raw[:2])
            if len(authors_raw) > 2:
                auth_str += " et al."
        else:
            auth_str = str(authors_raw)
        out.append({
            "title":          p.get("title", "N/A"),
            "source":         p.get("source", ""),
            "authors":        auth_str,
            "year":           str(p.get("year", "N/A")),
            "doi":            p.get("doi", ""),
            "url":            p.get("url", p.get("oa_pdf_url", "#")),
            "citation_count": p.get("citation_count", 0),
            "abstract":       p.get("abstract", ""),
            "oa_available":   bool(p.get("oa_pdf_url")),
        })
    return {"papers": out}


@app.get("/api/fetch-counts")
async def fetch_counts_endpoint():
    """Return per-source paper fetch counts for sidebar display."""
    if not pipeline:
        return {}
    return pipeline.get_fetch_counts()


@app.get("/api/session-stats")
async def session_stats_endpoint():
    """Return session memory and graph statistics (Module 4)."""
    if not pipeline:
        return {}
    return pipeline.get_session_stats()


@app.post("/api/upload-paper")
async def upload_paper_endpoint(
    file: UploadFile = File(...),
    question: str = Form(""),
):
    """
    Module 5: Upload PDF → semantic chunking → GraphRAG → grounded review.
    Uses same RAG pipeline as regular queries — not raw LLM generation.
    """
    if not pipeline:
        raise HTTPException(503, "Pipeline not ready yet")
    content    = await file.read()
    paper_text = extract_pdf_text(content)
    if not paper_text:
        raise HTTPException(400, "Could not extract text from PDF. Ensure it is a text-based PDF.")
    meta   = extract_paper_metadata(paper_text)
    review = pipeline.review_paper(paper_text, question)
    return {
        "review":    review,
        "title":     meta.get("title", file.filename),
        "filename":  file.filename,
        "char_count": len(paper_text),
    }


@app.post("/api/new-chat")
async def new_chat_endpoint():
    """
    Start a new conversation (clears history, keeps current paper index).
    Module 4: SessionMemory.clear_conversation()
    """
    if pipeline:
        pipeline.new_chat()
    return {"success": True, "message": "New conversation started. Paper index retained."}


@app.post("/api/clear")
async def clear_endpoint():
    """
    Full reset: clears conversation history + paper index + graph.
    Use when switching to a completely different research topic.
    """
    if pipeline:
        pipeline.clear_all()
    return {"success": True, "message": "Full reset complete."}


@app.get("/api/sessions")
async def sessions_endpoint():
    """Return session summary."""
    if not pipeline:
        return {}
    stats = pipeline.get_session_stats()
    return {
        "turns":           stats.get("turns", 0),
        "topics_queried":  stats.get("topics_queried", 0),
        "papers_indexed":  stats.get("papers_indexed", 0),
        "session_age_min": stats.get("session_age_min", 0),
    }
