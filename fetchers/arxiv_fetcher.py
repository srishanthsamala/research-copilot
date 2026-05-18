# ============================================================
# arxiv_fetcher.py — Fetch papers from arXiv (no API key needed)
# ============================================================
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from config import MAX_PAPERS_PER_SOURCE


def fetch_arxiv(query: str, max_results: int = MAX_PAPERS_PER_SOURCE) -> list[dict]:
    """
    Fetch papers from arXiv API sorted by relevance.
    Returns a list of paper dicts with metadata.
    """
    base_url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[arXiv] Fetch error: {e}")
        return []

    papers = []
    ns = {"atom": "http://www.w3.org/2005/Atom",
          "arxiv": "http://arxiv.org/schemas/atom"}

    root = ET.fromstring(response.content)
    for entry in root.findall("atom:entry", ns):
        try:
            title   = entry.find("atom:title", ns).text.strip().replace("\n", " ")
            summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
            authors = [a.find("atom:name", ns).text
                       for a in entry.findall("atom:author", ns)]
            arxiv_id = entry.find("atom:id", ns).text.strip().split("/")[-1]
            link    = f"https://arxiv.org/abs/{arxiv_id}"
            pdf_link = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

            # Published date
            pub_raw = entry.find("atom:published", ns)
            year    = pub_raw.text[:4] if pub_raw is not None else "N/A"

            papers.append({
                "source":       "arXiv",
                "title":        title,
                "authors":      authors,
                "abstract":     summary,
                "full_text":    summary,   # arXiv gives full abstract
                "year":         year,
                "url":          link,
                "pdf_url":      pdf_link,
                "doi":          arxiv_id,
                "citation_count": 0,       # Updated later by Semantic Scholar
            })
        except Exception as e:
            print(f"[arXiv] Parse error for entry: {e}")
            continue

    print(f"[arXiv] Fetched {len(papers)} papers for query: '{query}'")
    return papers
