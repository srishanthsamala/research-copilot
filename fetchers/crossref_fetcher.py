# ============================================================
# crossref_fetcher.py — Fetch papers from CrossRef API
# No API key required. Excellent for citation counts & DOIs.
# ============================================================
import requests
from config import MAX_PAPERS_PER_SOURCE


BASE_URL = "https://api.crossref.org/works"


def fetch_crossref(query: str, max_results: int = MAX_PAPERS_PER_SOURCE) -> list[dict]:
    """
    Fetch papers from CrossRef API sorted by relevance.
    CrossRef is especially good for citation counts & DOI resolution.
    """
    params = {
        "query":             query,
        "rows":              max_results,
        "sort":              "relevance",   # Relevance first, not citation count
        "order":             "desc",
        "select":            "title,author,abstract,published,DOI,URL,is-referenced-by-count,container-title",
        "mailto":            "research.copilot@academic.ai",
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"[CrossRef] Fetch error: {e}")
        return []

    papers = []
    items  = data.get("message", {}).get("items", [])

    for item in items:
        try:
            # Title
            titles = item.get("title", ["Untitled"])
            title  = titles[0] if titles else "Untitled"

            # Authors
            authors_raw = item.get("author", [])
            authors = [
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in authors_raw
            ]

            # Abstract (CrossRef often doesn't include it, that's okay)
            abstract = item.get("abstract", "")
            # Strip HTML tags from abstract if present
            if abstract:
                import re
                abstract = re.sub(r"<[^>]+>", "", abstract).strip()

            # Year
            pub_date = item.get("published", {}).get("date-parts", [[None]])
            year     = str(pub_date[0][0]) if pub_date and pub_date[0] and pub_date[0][0] else "N/A"

            doi      = item.get("DOI", "")
            url      = item.get("URL", f"https://doi.org/{doi}" if doi else "")
            journal  = item.get("container-title", [""])[0] if item.get("container-title") else ""
            cit_count = item.get("is-referenced-by-count", 0) or 0

            if not abstract:
                abstract = f"Paper from {journal}. DOI: {doi}. See full paper at {url}"

            papers.append({
                "source":         "CrossRef",
                "title":          title.strip(),
                "authors":        authors,
                "abstract":       abstract,
                "full_text":      abstract,
                "year":           year,
                "url":            url,
                "pdf_url":        f"https://doi.org/{doi}" if doi else "",
                "doi":            doi,
                "citation_count": cit_count,
                "journal":        journal,
            })
        except Exception as e:
            print(f"[CrossRef] Parse error: {e}")
            continue

    print(f"[CrossRef] Fetched {len(papers)} papers for query: '{query}'")
    return papers
