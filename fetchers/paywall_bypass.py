# ============================================================
# paywall_bypass.py — Module 3: Open Access & Unpaywall Fallback
#
# Strategy (ethical + legal):
#   1. Unpaywall API — checks for legal open-access versions
#   2. Semantic Scholar — often has full PDFs for CS papers
#   3. Direct institutional headers — passes Referer/UA from
#      college network session if configured (IEEE/Springer)
#   4. Europe PMC — open-access biomedical full texts
# ============================================================
import time
from typing import Optional
import requests


# ── Contact email for Unpaywall API (polite pool) ────────────
UNPAYWALL_EMAIL = "research@mvsrec.edu.in"  # Change to your college email


def get_open_access_pdf(doi: str, title: str = "") -> Optional[str]:
    """
    Try to find a legal open-access PDF for a paper.

    Tries in order:
      1. Unpaywall by DOI
      2. Semantic Scholar by title search
      3. Europe PMC by title/DOI

    Returns:
        Open-access PDF URL if found, else None
    """
    if not doi and not title:
        return None

    url = None

    # Strategy 1: Unpaywall (DOI-based, most reliable)
    if doi:
        url = _try_unpaywall(doi)

    # Strategy 2: Semantic Scholar (good for CS papers)
    if not url and title:
        url = _try_semantic_scholar_pdf(title)

    # Strategy 3: Europe PMC (biomedical)
    if not url and (doi or title):
        url = _try_europepmc(doi or title)

    if url:
        print(f"[PaywallBypass] ✓ Open access found: {url[:80]}...")
    return url


def _try_unpaywall(doi: str) -> Optional[str]:
    """Query Unpaywall for open-access version by DOI."""
    doi_clean = doi.replace("https://doi.org/", "").strip()
    if not doi_clean:
        return None
    try:
        resp = requests.get(
            f"https://api.unpaywall.org/v2/{doi_clean}",
            params={"email": UNPAYWALL_EMAIL},
            timeout=5,
            headers={"User-Agent": "AcademicCopilot/2.0"},
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("is_oa"):
                # Get best open access location
                best = data.get("best_oa_location") or {}
                pdf_url = best.get("url_for_pdf") or best.get("url")
                return pdf_url
    except Exception as e:
        print(f"[Unpaywall] Error: {e}")
    return None


def _try_semantic_scholar_pdf(title: str) -> Optional[str]:
    """Query Semantic Scholar for open-access PDF by paper title."""
    try:
        resp = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query":  title[:100],
                "fields": "openAccessPdf,externalIds",
                "limit":  1,
            },
            timeout=5,
            headers={"User-Agent": "AcademicCopilot/2.0"},
        )
        if resp.status_code == 200:
            results = resp.json().get("data", [])
            if results:
                oa_pdf = results[0].get("openAccessPdf", {})
                return oa_pdf.get("url") if oa_pdf else None
    except Exception as e:
        print(f"[SemanticScholarPDF] Error: {e}")
    return None


def _try_europepmc(query: str) -> Optional[str]:
    """Query Europe PMC for open-access biomedical papers."""
    try:
        resp = requests.get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={
                "query":    query[:100],
                "format":   "json",
                "resulttype": "core",
                "pageSize": 1,
            },
            timeout=5,
        )
        if resp.status_code == 200:
            results = resp.json().get("resultList", {}).get("result", [])
            for r in results:
                if r.get("isOpenAccess") == "Y":
                    pmid = r.get("pmid", "")
                    if pmid:
                        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{r.get('pmcid','').replace('PMC','')}/pdf/"
    except Exception as e:
        print(f"[EuropePMC] Error: {e}")
    return None


class InstitutionalSession:
    """
    Maintains an HTTP session with institutional headers.
    When the user is on college WiFi, IEEE and Springer may
    grant expanded access via IP-based authentication.
    Configure JSESSIONID / cookies from your college proxy below.
    """

    # ── Configure these from your browser when on college WiFi ──
    IEEE_SESSION_COOKIE     = ""    # e.g. "JSESSIONID=abc123..."
    SPRINGER_SESSION_COOKIE = ""    # e.g. "SpringerSession=xyz..."
    INSTITUTION_REFERER     = "https://ieeexplore.ieee.org/"

    @classmethod
    def build_ieee_session(cls) -> requests.Session:
        """Build a requests Session with IEEE institutional headers."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Referer": cls.INSTITUTION_REFERER,
            "Accept":  "application/json, text/html",
        })
        if cls.IEEE_SESSION_COOKIE:
            session.headers["Cookie"] = cls.IEEE_SESSION_COOKIE
        return session

    @classmethod
    def build_springer_session(cls) -> requests.Session:
        """Build a requests Session with Springer institutional headers."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Referer": "https://link.springer.com/",
        })
        if cls.SPRINGER_SESSION_COOKIE:
            session.headers["Cookie"] = cls.SPRINGER_SESSION_COOKIE
        return session
