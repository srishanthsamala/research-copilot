# ============================================================
# springer_fetcher.py — Springer Nature API Fetcher
#
# FREE API key → https://dev.springernature.com
#   Register → My Apps → New App → copy API key
#   Paste into config.py: SPRINGER_API_KEY = "your_key"
#
# Without key: fetches from Springer Open Access automatically.
# With key:    fetches from all Springer journals (full metadata).
# ============================================================
import time
import requests
from config import SPRINGER_API_KEY, MAX_PAPERS_PER_SOURCE

SPRINGER_META_URL = "https://api.springernature.com/meta/v2/json"
SPRINGER_OPEN_URL = "https://api.springernature.com/openaccess/json"

HEADERS = {
    "User-Agent": "ScholarGraphite/2.0 (academic research; contact: research@mvsrec.edu.in)",
    "Accept":     "application/json",
}


def fetch_springer(query: str, max_results: int = MAX_PAPERS_PER_SOURCE) -> list[dict]:
    """
    Fetch papers from Springer Nature.
    With key    → full metadata API (all journals)
    Without key → open-access API (free CS/engineering papers)
    """
    has_key = SPRINGER_API_KEY and SPRINGER_API_KEY != "your_springer_api_key_here"

    if has_key:
        papers = _fetch_meta_api(query, max_results, SPRINGER_API_KEY)
        if papers:
            return papers
        print("[Springer] Meta API returned 0 — falling back to open access.")

    return _fetch_open_access(query, max_results)


def _fetch_meta_api(query: str, max_results: int, api_key: str) -> list[dict]:
    """Full metadata API — all Springer journals."""
    # Use keyword search without quotes for maximum results
    params = {
        "api_key": api_key,
        "q":       query,
        "p":       max_results,
        "s":       1,
    }
    try:
        resp = requests.get(SPRINGER_META_URL, params=params,
                            headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"[Springer] Meta API HTTP {resp.status_code}: {resp.text[:150]}")
            return []
        records = resp.json().get("records", [])
        papers  = [_parse(r) for r in records]
        papers  = [p for p in papers if p]
        print(f"[Springer] {len(papers)} papers (meta API).")
        return papers
    except Exception as e:
        print(f"[Springer] Meta API error: {e}")
        return []


def _fetch_open_access(query: str, max_results: int) -> list[dict]:
    """
    Springer Open Access — no API key needed.
    Covers open-access CS, engineering, and sciences articles.
    """
    # Try two query formats for best coverage
    for q_format in [query, f"title:{query.split()[0]}"]:
        try:
            params = {"q": q_format, "p": max_results, "s": 1}
            resp = requests.get(SPRINGER_OPEN_URL, params=params,
                                headers=HEADERS, timeout=15)
            if resp.status_code == 429:
                print("[Springer Open] Rate limited — skipping.")
                return []
            if resp.status_code != 200:
                print(f"[Springer Open] HTTP {resp.status_code}")
                continue
            records = resp.json().get("records", [])
            if records:
                papers = [_parse(r, open_access=True) for r in records]
                papers = [p for p in papers if p]
                print(f"[Springer Open] {len(papers)} open-access papers.")
                return papers
        except Exception as e:
            print(f"[Springer Open] Error: {e}")
            time.sleep(1)

    print("[Springer Open] No results.")
    return []


def _parse(rec: dict, open_access: bool = False) -> dict | None:
    """Parse one Springer record into the normalised paper format."""
    try:
        title = (rec.get("title") or "").strip()
        if not title:
            return None

        # Authors
        authors = [
            c.get("creator", "").strip()
            for c in rec.get("creators", [])
            if c.get("creator")
        ]

        # Abstract
        abstract = (rec.get("abstract") or "").strip()

        # DOI
        doi = rec.get("doi", "")

        # URL
        url_field = rec.get("url", [])
        if isinstance(url_field, list) and url_field:
            link = url_field[0].get("value", "")
        elif isinstance(url_field, str):
            link = url_field
        else:
            link = f"https://doi.org/{doi}" if doi else ""

        # Year
        pub_date = rec.get("publicationDate") or rec.get("onlineDate") or "N/A"
        year     = str(pub_date)[:4]

        # PDF
        if open_access and doi:
            pdf_url = f"https://link.springer.com/content/pdf/{doi}.pdf"
        elif doi:
            pdf_url = f"https://doi.org/{doi}"
        else:
            pdf_url = link

        return {
            "source":         "Springer",
            "title":          title,
            "authors":        authors,
            "abstract":       abstract,
            "full_text":      abstract,
            "year":           year,
            "url":            link or f"https://doi.org/{doi}",
            "pdf_url":        pdf_url,
            "doi":            doi,
            "citation_count": 0,     # Enriched later by Semantic Scholar
            "journal":        rec.get("publicationName", ""),
            "open_access":    open_access,
        }
    except Exception as e:
        print(f"[Springer] Parse error: {e}")
        return None
