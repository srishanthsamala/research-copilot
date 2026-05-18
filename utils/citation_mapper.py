# ============================================================
# citation_mapper.py — Maps LLM-generated insights to source papers
# Automated citation verification & linking
# ============================================================
from typing import List, Dict


class CitationMapper:
    """
    Tracks all papers ingested in a session and maps
    LLM-generated answers back to their source documents.
    """

    def __init__(self):
        self._papers: Dict[str, Dict] = {}   # title (normalized) → paper metadata

    def register_paper(self, paper: dict):
        """Register a paper so it can be cited later."""
        key = self._normalize(paper.get("title", ""))
        if key:
            self._papers[key] = {
                "title":          paper.get("title", ""),
                "authors":        paper.get("authors", []),
                "year":           paper.get("year", "N/A"),
                "source":         paper.get("source", ""),
                "url":            paper.get("url", ""),
                "doi":            paper.get("doi", ""),
                "citation_count": paper.get("citation_count", 0),
                "journal":        paper.get("journal", ""),
            }

    def extract_cited_papers(self, retrieved_chunks: List[Dict]) -> List[Dict]:
        """
        Extract unique papers from retrieved chunks.
        Returns a deduplicated, citation-count-sorted list of cited papers.
        """
        seen   = set()
        papers = []

        for chunk in retrieved_chunks:
            title = chunk.get("paper_title", "")
            key   = self._normalize(title)

            if key and key not in seen:
                seen.add(key)
                paper_data = self._papers.get(key, {})
                papers.append({
                    "title":          title,
                    "authors":        chunk.get("paper_authors", []),
                    "year":           chunk.get("paper_year", "N/A"),
                    "source":         chunk.get("paper_source", ""),
                    "url":            chunk.get("paper_url", ""),
                    "doi":            chunk.get("paper_doi", ""),
                    "citation_count": chunk.get("citation_count", 0),
                    "journal":        paper_data.get("journal", ""),
                    "relevance_score": chunk.get("relevance_score", 0),
                })

        # Sort by citation count descending (most impactful papers first)
        papers.sort(key=lambda x: x["citation_count"], reverse=True)
        return papers

    def format_citation(self, paper: dict, index: int = None) -> str:
        """Format a paper as an inline citation string."""
        authors = paper.get("authors", [])
        if authors:
            first_author = authors[0].split(",")[0].split()[-1] if authors[0] else "Unknown"
            if len(authors) > 1:
                author_str = f"{first_author} et al."
            else:
                author_str = first_author
        else:
            author_str = "Unknown"

        year   = paper.get("year", "N/A")
        title  = paper.get("title", "")
        doi    = paper.get("doi", "")
        url    = paper.get("url", "")
        source = paper.get("source", "")

        citation = f"{author_str} ({year}). {title}. [{source}]"
        if doi:
            citation += f" DOI: {doi}"
        elif url:
            citation += f" URL: {url}"

        if index is not None:
            citation = f"[{index}] " + citation

        return citation

    def format_reference_list(self, papers: List[Dict]) -> str:
        """Generate a formatted reference list from cited papers."""
        if not papers:
            return "No references found."

        lines = ["## 📚 References\n"]
        for i, paper in enumerate(papers, 1):
            lines.append(self.format_citation(paper, index=i))
            citation_str = f"{paper.get('citation_count', 0):,}"
            lines.append(f"   ↳ Cited by {citation_str} papers | Source: {paper.get('source', 'N/A')}\n")

        return "\n".join(lines)

    def clear(self):
        """Reset for new query session."""
        self._papers.clear()

    @staticmethod
    def _normalize(title: str) -> str:
        """Normalize title for deduplication."""
        return title.lower().strip()[:100]
