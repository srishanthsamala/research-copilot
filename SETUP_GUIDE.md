# Scholar Graphite v2 — Setup Guide

## What's New in v2

Five major modules added to the original Academic Co-Pilot:

- **Module 1** — Smart query expansion (LLM converts your question to precise search terms) + semantic relevance-first ranking + honest guardrails ("insufficient data" responses)
- **Module 2** — Semantic chunking (splits at meaning boundaries, not fixed chars) + GraphRAG knowledge graph with multi-hop retrieval
- **Module 3** — Unpaywall open-access PDF fallback for paywalled papers
- **Module 4** — Session memory (same topic → no re-fetch) + multi-stage comparison (methodology → metrics table → consensus)
- **Module 5** — PDF upload chat via full RAG pipeline (not raw LLM)

## Architecture

```
Browser (localhost:3000)
    ↕  Vite proxy
React Frontend (frontend/ — Stitch design)
    ↕  REST API  /api/*
FastAPI Backend (backend.py — port 8000)
    ↕
RAGPipeline v2:
  QueryExpander → Fetchers × 6 → Unpaywall OA
  → SemanticRanker → SemanticChunker
  → FAISS + GraphRAG → SessionMemory
  → Groq LLaMA 3.3 70B (honest guardrails)
```

---

## One-time Setup

### 1 — Python backend

```cmd
cd academic_copilot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2 — API Keys (config.py)

Open `config.py` and fill in:

```python
GROQ_API_KEY     = "gsk_..."   # Required — groq.com (free)
IEEE_API_KEY     = "..."       # Optional
SPRINGER_API_KEY = "..."       # Optional
```

### 3 — Node / npm (for frontend)

Install Node.js from https://nodejs.org (LTS version), then:

```cmd
cd frontend
npm install
```

---

## Running the App

Open **two separate Command Prompt windows**:

**Terminal 1 — Backend:**
```cmd
cd academic_copilot
start_backend.bat
```

**Terminal 2 — Frontend:**
```cmd
cd academic_copilot
start_frontend.bat
```

Open **http://localhost:3000** in your browser.

---

## File Structure

```
academic_copilot/
├── backend.py              ← FastAPI server (all /api/* endpoints)
├── config.py               ← API keys + model config
├── rag_pipeline.py         ← Core RAG orchestration
├── requirements.txt        ← Python dependencies
├── start_backend.bat       ← Start backend
├── start_frontend.bat      ← Start frontend
│
├── frontend/               ← React/Vite (exact Stitch design)
│   ├── src/
│   │   ├── App.tsx             ← Main app, tabs, API calls
│   │   ├── index.css           ← Tailwind + Stitch design tokens
│   │   └── components/
│   │       ├── Header.tsx      ← Nav + New Chat
│   │       ├── Sidebar.tsx     ← Live counts + PDF upload
│   │       ├── ChatInput.tsx   ← Query textarea + send
│   │       ├── ChatMessage.tsx ← User/AI bubbles + citations
│   │       ├── CompareTab.tsx  ← Paper comparison
│   │       └── LibraryTab.tsx  ← Fetched papers browser
│   ├── vite.config.ts          ← Proxies /api → port 8000
│   └── package.json
│
├── fetchers/               ← arXiv, IEEE, Springer, Semantic Scholar, PubMed, CrossRef
├── embeddings/             ← Chunking + HuggingFace embedder
├── vector_store/           ← FAISS IndexFlatIP
├── llm/                    ← Groq LLaMA 3.3 70B wrapper
└── utils/                  ← Citation mapper, PDF parser, ranker
```

---

## API Endpoints

| Method | Endpoint            | What it does                       |
|--------|---------------------|------------------------------------|
| GET    | /api/health         | Health check                       |
| POST   | /api/query          | RAG query → answer + citations     |
| POST   | /api/compare        | Compare 2–5 papers                 |
| GET    | /api/papers         | All fetched papers this session    |
| GET    | /api/fetch-counts   | Per-source paper counts            |
| POST   | /api/upload-paper   | Upload PDF → AI review             |
| POST   | /api/new-chat       | Start new session                  |
| POST   | /api/clear          | Clear current chat                 |

Interactive API docs: **http://localhost:8000/docs**
