# ============================================================
# pdf_parser.py — Extract text from user-uploaded PDF papers
# Uses PyMuPDF (fitz) for reliable academic PDF parsing
# ============================================================
import io
import re
from typing import Optional


def extract_pdf_text(file_bytes: bytes) -> str:
    """
    Extract clean text from a PDF file.

    Args:
        file_bytes: Raw bytes of the uploaded PDF file

    Returns:
        Cleaned extracted text string
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return _fallback_pypdf(file_bytes)

    try:
        doc  = fitz.open(stream=file_bytes, filetype="pdf")
        text_parts = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if text.strip():
                text_parts.append(f"[Page {page_num + 1}]\n{text}")

        doc.close()
        full_text = "\n".join(text_parts)
        return _clean_text(full_text)

    except Exception as e:
        print(f"[PDFParser] PyMuPDF error: {e}, trying fallback...")
        return _fallback_pypdf(file_bytes)


def _fallback_pypdf(file_bytes: bytes) -> str:
    """Fallback PDF parser using PyPDF2."""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                text_parts.append(f"[Page {i + 1}]\n{text}")
        return _clean_text("\n".join(text_parts))
    except Exception as e:
        print(f"[PDFParser] PyPDF2 error: {e}")
        return ""


def _clean_text(text: str) -> str:
    """Clean extracted PDF text for LLM consumption."""
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    # Remove page headers/footers patterns (common in academic PDFs)
    text = re.sub(r'\[Page \d+\]\n', '\n', text)
    # Remove common PDF artifacts
    text = re.sub(r'([a-z])-\n([a-z])', r'\1\2', text)  # Fix hyphenation
    return text.strip()


def extract_paper_metadata(text: str) -> dict:
    """
    Try to extract basic metadata from PDF text (title, authors).
    Useful for display purposes when no API metadata is available.
    """
    lines  = [l.strip() for l in text.split('\n') if l.strip()]
    title  = lines[0] if lines else "Uploaded Paper"

    # Simple heuristic: look for author patterns in first 20 lines
    authors = []
    for line in lines[1:20]:
        # Pattern: names separated by commas or "and"
        if re.search(r'\b(University|Institute|Department|Lab|@)\b', line, re.IGNORECASE):
            break
        if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+', line) and len(line) < 100:
            authors.append(line)
        if len(authors) >= 5:
            break

    return {
        "title":   title[:200],
        "authors": authors,
        "source":  "Uploaded PDF",
    }
