# ============================================================
# groq_llm.py — Groq API client for LLaMA 3 70B inference
# Free API key at: https://console.groq.com
# ============================================================
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL, RAG_SYSTEM_PROMPT, COMPARISON_SYSTEM_PROMPT


class GroqLLM:
    """
    Wrapper for Groq's LLaMA 3 70B API.
    Used for grounded RAG generation and paper comparison.
    """

    def __init__(self):
        if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
            raise ValueError(
                "Groq API key not set. Get your free key at https://console.groq.com "
                "and add it to config.py or set GROQ_API_KEY environment variable."
            )
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model  = GROQ_MODEL
        print(f"[GroqLLM] Initialized with model: {self.model}")

    def generate_rag_answer(
        self,
        query: str,
        context_chunks: list[dict],
        conversation_history: list[dict] = None,
    ) -> str:
        """
        Generate a grounded answer using retrieved paper chunks.
        Strictly uses only the provided context — no hallucination.

        Args:
            query:                User's query
            context_chunks:       Retrieved chunks from FAISS
            conversation_history: Prior messages in this session [{"role": ..., "content": ...}]

        Returns:
            Generated answer string with inline citations.
        """
        if not context_chunks:
            return (
                "⚠️ No relevant papers were retrieved for your query. "
                "Please try different keywords or check your API configurations."
            )

        # Build context block from retrieved chunks
        context_block = self._build_context_block(context_chunks)

        # Build messages
        messages = [{"role": "system", "content": RAG_SYSTEM_PROMPT}]

        # Add conversation history for follow-up context (last 6 turns)
        if conversation_history:
            messages.extend(conversation_history[-6:])

        # Add current query with context
        user_message = f"""RETRIEVED PAPER EXCERPTS:
{context_block}

---
USER QUESTION: {query}

Please answer ONLY using the paper excerpts above. Cite every claim with [Paper Title, Authors, Year].
"""
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,    # Low temperature for factual accuracy
                max_tokens=2048,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ LLM Error: {str(e)}"

    def generate_comparison(self, papers: list[dict]) -> str:
        """
        Generate a structured side-by-side comparison of multiple papers.

        Args:
            papers: List of paper dicts with abstract/full_text

        Returns:
            Structured comparison markdown string.
        """
        if not papers:
            return "No papers provided for comparison."

        papers_block = ""
        for i, paper in enumerate(papers, 1):
            papers_block += f"""
PAPER {i}:
Title: {paper.get('title', 'N/A')}
Authors: {', '.join(paper.get('authors', [])[:3])}
Year: {paper.get('year', 'N/A')}
Source: {paper.get('source', 'N/A')}
Citation Count: {paper.get('citation_count', 0):,}
Abstract/Content: {paper.get('abstract', paper.get('full_text', 'Not available'))[:1500]}
---"""

        prompt = f"""Compare the following {len(papers)} research papers in a structured format.

{papers_block}

Generate a detailed structured comparison covering:
1. **Research Objective** — What problem does each paper solve?
2. **Methodology** — What approach/technique does each paper use?
3. **Dataset Used** — What data was used (if mentioned)?
4. **Key Results & Metrics** — What were the main findings?
5. **Limitations** — What are the stated or apparent limitations?
6. **Impact** — Citation count and research significance.

End with a **Summary Table** in markdown format comparing all papers side by side.
ONLY use information from the papers provided. Do not add external knowledge."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": COMPARISON_SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.1,
                max_tokens=3000,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Comparison Error: {str(e)}"

    def review_uploaded_paper(self, paper_text: str, user_question: str = "") -> str:
        """
        Review a user-uploaded research paper and provide structured analysis.

        Args:
            paper_text:    Extracted text from the uploaded PDF
            user_question: Optional specific question about the paper

        Returns:
            Structured review markdown string.
        """
        if not paper_text.strip():
            return "Could not extract text from the uploaded paper."

        question_part = f"\nSpecifically, the user asks: {user_question}" if user_question else ""

        prompt = f"""Analyze the following research paper and provide a comprehensive structured review.

PAPER CONTENT (first 3000 chars):
{paper_text[:3000]}

{question_part}

Provide your review in the following structure:
1. **Paper Title & Authors** (as detected)
2. **Research Objective** — What problem does it address?
3. **Methodology Summary** — What approach is used?
4. **Key Contributions** — What are the novel contributions?
5. **Results & Findings** — What were the main results?
6. **Limitations** — What are the weaknesses or gaps?
7. **Research Quality Assessment** — Clarity, rigor, impact potential (rate 1-5)
8. **Suggested Follow-up Papers** — Topics to explore next (do NOT fabricate specific papers)

Base your review ONLY on the provided paper text."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert academic paper reviewer. Provide structured, rigorous, and honest reviews based only on the paper content provided."},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2500,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Review Error: {str(e)}"

    @staticmethod
    def _build_context_block(chunks: list[dict]) -> str:
        """
        Format retrieved chunks into a numbered context block for the LLM.
        Module 1: sorted by relevance score (FAISS cosine sim) first,
        then by citation count — relevance-first in context window.
        """
        # Sort by relevance_score descending, then citation count
        sorted_chunks = sorted(
            chunks,
            key=lambda x: (x.get("relevance_score", 0.0), x.get("citation_count", 0)),
            reverse=True,
        )

        block = ""
        for i, chunk in enumerate(sorted_chunks, 1):
            authors_str = ", ".join(chunk.get("paper_authors", [])[:3])
            if len(chunk.get("paper_authors", [])) > 3:
                authors_str += " et al."
            block += f"""[EXCERPT {i}]
Title: {chunk.get('paper_title', 'Unknown')}
Authors: {authors_str}
Year: {chunk.get('paper_year', 'N/A')}
Source: {chunk.get('paper_source', 'N/A')} | Citations: {chunk.get('citation_count', 0):,}
DOI/URL: {chunk.get('paper_doi', chunk.get('paper_url', 'N/A'))}
Relevance Score: {chunk.get('relevance_score', 0):.3f}
Content: {chunk.get('text', '')}

"""
        return block
