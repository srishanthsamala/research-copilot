# ============================================================
# semantic_scholar_fetcher.py — Semantic Scholar API Fetcher
# No API key required. 200M+ papers, citation counts included.
# ============================================================
import time
import requests
from config import MAX_PAPERS_PER_SOURCE

S2_BASE  = "https://api.semanticscholar.org/graph/v1"
FIELDS   = "title,authors,year,abstract,citationCount,externalIds,url,openAccessPdf"
HEADERS  = {
    "User-Agent": "ScholarGraphite/2.0 (academic research tool; contact: research@mvsrec.edu.in)",
    "Accept":     "application/json",
}


def fetch_semantic_scholar(query: str, max_results: int = MAX_PAPERS_PER_SOURCE) -> list[dict]:
    """
    Search Semantic Scholar for papers matching the query.
    Returns papers sorted by citation count (highest first).
    """
    params = {
        "query":  query,
        "limit":  min(max_results, 100),
        "fields": FIELDS,
    }

    for attempt in range(3):
        try:
            resp = requests.get(
                f"{S2_BASE}/paper/search",
                params=params,
                headers=HEADERS,
                timeout=15,
            )
            if resp.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"[SemanticScholar] Rate limited — waiting {wait}s...")
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                print(f"[SemanticScholar] HTTP {resp.status_code}: {resp.text[:150]}")
                return []
            data = resp.json()
            break
        except requests.RequestException as e:
            print(f"[SemanticScholar] Fetch error (attempt {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(2)
            else:
                return []
    else:
        return []

    papers = []
    for item in data.get("data", []):
        try:
            authors  = [a.get("name", "") for a in item.get("authors", [])]
            abstract = item.get("abstract") or ""
            ext_ids  = item.get("externalIds") or {}
            doi      = ext_ids.get("DOI", "")
            arxiv_id = ext_ids.get("ArXiv", "")
            pdf_info = item.get("openAccessPdf") or {}
            pdf_url  = pdf_info.get("url", "")

            papers.append({
                "source":         "Semantic Scholar",
                "title":          (item.get("title") or "Untitled").strip(),
                "authors":        [a for a in authors if a],
                "abstract":       abstract,
                "full_text":      abstract,
                "year":           str(item.get("year") or "N/A"),
                "url":            item.get("url") or "",
                "pdf_url":        pdf_url or (f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else ""),
                "doi":            doi,
                "citation_count": int(item.get("citationCount") or 0),
                "paper_id":       item.get("paperId", ""),
            })
        except Exception as e:
            print(f"[SemanticScholar] Parse error: {e}")
            continue

    papers.sort(key=lambda x: x["citation_count"], reverse=True)
    print(f"[SemanticScholar] {len(papers)} papers fetched.")
    return papers


def enrich_citation_counts(papers: list[dict]) -> list[dict]:
    """
    Enrich papers from other sources with citation counts via Semantic Scholar.
    Batches by DOI lookup to minimise API calls and avoid rate limits.
    Only processes papers that have a DOI and currently have 0 citations.
    """
    to_enrich = [p for p in papers if not p.get("citation_count") and p.get("doi")]

    if not to_enrich:
        return papers

    # Build a DOI → paper index for fast update
    doi_map = {p["doi"]: p for p in to_enrich if p.get("doi")}

    # Lookup each DOI (batching not supported by S2 free tier, but limit calls)
    enriched_count = 0
    for doi, paper in list(doi_map.items())[:20]:   # Cap at 20 to avoid rate limits
        try:
            resp = requests.get(
                f"{S2_BASE}/paper/DOI:{doi}",
                params={"fields": "citationCount"},
                headers=HEADERS,
                timeout=6,
            )
            if resp.status_code == 200:
                count = resp.json().get("citationCount") or 0
                paper["citation_count"] = int(count)
                enriched_count += 1
            elif resp.status_code == 429:
                print("[SemanticScholar] Rate limit during enrichment — stopping early.")
                break
            time.sleep(0.15)   # Polite delay between requests
        except Exception:
            continue

    if enriched_count:
        print(f"[SemanticScholar] Enriched {enriched_count} citation counts.")
    return papers
