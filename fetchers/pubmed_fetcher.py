# ============================================================
# pubmed_fetcher.py — Fetch papers from PubMed (NIH)
# No API key required.
# ============================================================
import requests
import xml.etree.ElementTree as ET
from config import MAX_PAPERS_PER_SOURCE


ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def fetch_pubmed(query: str, max_results: int = MAX_PAPERS_PER_SOURCE) -> list[dict]:
    """
    Fetch papers from PubMed using NCBI E-utilities.
    Returns paper metadata with abstracts.
    """
    # Step 1: Search for IDs
    try:
        search_resp = requests.get(ESEARCH_URL, params={
            "db":      "pubmed",
            "term":    query,
            "retmax":  max_results,
            "retmode": "json",
            "sort":    "relevance",
        }, timeout=15)
        search_resp.raise_for_status()
        ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"[PubMed] Search error: {e}")
        return []

    if not ids:
        print(f"[PubMed] No results for query: '{query}'")
        return []

    # Step 2: Fetch full records
    try:
        fetch_resp = requests.get(EFETCH_URL, params={
            "db":      "pubmed",
            "id":      ",".join(ids),
            "retmode": "xml",
        }, timeout=20)
        fetch_resp.raise_for_status()
    except Exception as e:
        print(f"[PubMed] Fetch error: {e}")
        return []

    papers = []
    root   = ET.fromstring(fetch_resp.content)

    for article in root.findall(".//PubmedArticle"):
        try:
            # Title
            title_el = article.find(".//ArticleTitle")
            title    = title_el.text if title_el is not None else "Untitled"
            if title:
                title = title.strip()

            # Abstract
            abstract_parts = article.findall(".//AbstractText")
            abstract = " ".join(
                (el.get("Label", "") + ": " + (el.text or "")).strip()
                for el in abstract_parts
            ).strip()

            # Authors
            authors = []
            for author in article.findall(".//Author"):
                last  = author.find("LastName")
                first = author.find("ForeName")
                if last is not None:
                    name = last.text
                    if first is not None:
                        name += f", {first.text}"
                    authors.append(name)

            # Year
            year_el = article.find(".//PubDate/Year")
            year    = year_el.text if year_el is not None else "N/A"

            # PMID
            pmid_el = article.find(".//PMID")
            pmid    = pmid_el.text if pmid_el is not None else ""

            # DOI
            doi = ""
            for eloc in article.findall(".//ELocationID"):
                if eloc.get("EIdType") == "doi":
                    doi = eloc.text or ""
                    break

            papers.append({
                "source":         "PubMed",
                "title":          title,
                "authors":        authors,
                "abstract":       abstract,
                "full_text":      abstract,
                "year":           year,
                "url":            f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "pdf_url":        f"https://www.ncbi.nlm.nih.gov/pmc/articles/pmid/{pmid}/pdf/" if pmid else "",
                "doi":            doi,
                "citation_count": 0,   # Enriched later by Semantic Scholar
                "pmid":           pmid,
            })
        except Exception as e:
            print(f"[PubMed] Parse error: {e}")
            continue

    print(f"[PubMed] Fetched {len(papers)} papers for query: '{query}'")
    return papers
