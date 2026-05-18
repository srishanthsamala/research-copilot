# ============================================================
# ieee_fetcher.py — IEEE Xplore API Fetcher
#
# API key: FREE at https://developer.ieee.org
#   → Register → Create Application → Copy API key
#   → Paste into config.py: IEEE_API_KEY = "your_key"
#
# Without a key: falls back to IEEE open-search (limited).
# With a key: full metadata, abstracts, citation counts.
# ============================================================
import requests
from config import IEEE_API_KEY, MAX_PAPERS_PER_SOURCE

IEEE_BASE = "https://ieeexploreapi.ieee.org/api/v1/search/articles"


def fetch_ieee(query: str, max_results: int = MAX_PAPERS_PER_SOURCE) -> list[dict]:
    """
    Fetch papers from IEEE Xplore.
    Returns normalised paper dicts with title, abstract, authors,
    year, DOI, URL, and citation count.
    """
    if not IEEE_API_KEY or IEEE_API_KEY == "your_ieee_api_key_here":
        print("[IEEE] No API key — using open fallback.")
        return _fetch_ieee_open(query, max_results)

    params = {
        "apikey":       IEEE_API_KEY,
        "querytext":    query,
        "max_records":  max_results,
        "sort_field":   "publication_year",   # Valid IEEE sort field
        "sort_order":   "desc",               # Most recent first
        "start_record": 1,
        "format":       "json",
    }

    try:
        resp = requests.get(IEEE_BASE, params=params, timeout=15,
                            headers={"Accept": "application/json"})
        if resp.status_code != 200:
            print(f"[IEEE] HTTP {resp.status_code}: {resp.text[:200]}")
            return []
        data = resp.json()
    except requests.RequestException as e:
        print(f"[IEEE] Fetch error: {e}")
        return []
    except ValueError:
        print("[IEEE] Invalid JSON response.")
        return []

    # API can return an error message in the JSON itself
    if "message" in data and "articles" not in data:
        print(f"[IEEE] API message: {data['message']}")
        return []

    papers = []
    for article in data.get("articles", []):
        paper = _parse_article(article)
        if paper:
            papers.append(paper)

    print(f"[IEEE] {len(papers)} papers fetched.")
    return papers


def _parse_article(article: dict) -> dict | None:
    """Parse one IEEE article dict into the normalised paper format."""
    try:
        title = article.get("title", "").strip()
        if not title:
            return None

        authors_raw = article.get("authors", {}).get("authors", [])
        authors = [
            a.get("full_name", a.get("first_name","") + " " + a.get("last_name","")).strip()
            for a in authors_raw
        ]
        authors = [a for a in authors if a.strip()]

        abstract  = article.get("abstract", "").strip()
        doi       = article.get("doi", "")
        art_num   = str(article.get("article_number", ""))
        url       = article.get("html_url") or \
                    (f"https://ieeexplore.ieee.org/document/{art_num}" if art_num else "")
        year      = str(article.get("publication_year", "N/A"))
        citations = int(article.get("citing_paper_count", 0) or 0)
        journal   = article.get("publication_title", "")

        # Build institutional PDF URL (works on college WiFi/VPN)
        pdf_url = ""
        if art_num:
            pdf_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber={art_num}"
        elif doi:
            pdf_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doi.split('/')[-1]}"

        return {
            "source":         "IEEE",
            "title":          title,
            "authors":        authors,
            "abstract":       abstract,
            "full_text":      abstract,
            "year":           year,
            "url":            url,
            "pdf_url":        pdf_url,
            "doi":            doi,
            "citation_count": citations,
            "journal":        journal,
        }
    except Exception as e:
        print(f"[IEEE] Parse error: {e}")
        return None


def _fetch_ieee_open(query: str, max_results: int) -> list[dict]:
    """
    Fallback: use IEEE open metadata search (no API key needed).
    Returns limited results — get a free key for full access.
    """
    try:
        # IEEE open search endpoint (public, no auth)
        resp = requests.get(
            "https://ieeexploreapi.ieee.org/api/v1/search/articles",
            params={
                "querytext":   query,
                "max_records": min(max_results, 5),   # Limited without key
                "format":      "json",
            },
            timeout=10,
            headers={"Accept": "application/json"},
        )
        # Without a key this returns a 401 — that's expected
        if resp.status_code in (200, 206):
            papers = []
            for art in resp.json().get("articles", []):
                p = _parse_article(art)
                if p:
                    papers.append(p)
            print(f"[IEEE open] {len(papers)} papers.")
            return papers
    except Exception as e:
        print(f"[IEEE open] Error: {e}")
    return []
