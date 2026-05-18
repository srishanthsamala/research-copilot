# ============================================================
# query_expander.py — Module 1: Semantic Query Expansion
# Uses Groq LLaMA to expand user's natural language query into
# precise academic search terms before dispatching to APIs.
# ============================================================
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL


_EXPANSION_SYSTEM = """You are an academic search assistant.
Convert the user's question into a list of precise academic search keywords.
Output ONLY a JSON object in this exact format:
{
  "primary_query": "the best single search string for academic APIs",
  "synonyms": ["alt term 1", "alt term 2"],
  "technical_terms": ["specific technical term 1", "specific technical term 2"],
  "domain": "the research domain/field (e.g. NLP, Computer Vision, Bioinformatics)"
}
Rules:
- primary_query should be 3-6 meaningful technical words
- Remove all question words (what, how, why), articles, prepositions
- Expand abbreviations (RAG → Retrieval Augmented Generation)
- Include domain-specific terminology
- NO sentences, ONLY keyword phrases"""


class QueryExpander:
    """
    LLM-powered query expansion for better academic search relevance.
    Falls back to simple keyword extraction if LLM call fails.
    """

    STOP_WORDS = {
        "what","are","is","the","a","an","of","in","to","for","on","at","by",
        "from","with","about","as","into","through","during","before","after",
        "above","below","between","out","off","over","under","again","further",
        "then","once","here","there","when","where","why","how","all","both",
        "each","few","more","most","other","some","such","no","nor","not",
        "only","own","same","so","than","too","very","can","will","just",
        "should","now","tell","me","us","give","show","please","latest",
        "recent","new","old","any","its","it","this","that","these","those",
        "i","you","he","she","we","they","do","did","does","has","have","had",
        "be","been","being","am","was","were","would","could","might","may",
        "shall","summarize","explain","describe","compare","review","analyze",
        "find","get","make","take","use","using","used","based","related",
        "paper","papers","research","study","studies","article","articles",
        "also","even","still","yet","well","often","many","much","little",
        "your","our","their","my","his","her","and","or","but","if","while",
    }

    def __init__(self):
        try:
            self.client = Groq(api_key=GROQ_API_KEY)
            self.model  = GROQ_MODEL
            self._enabled = True
        except Exception:
            self._enabled = False

    def expand(self, user_query: str) -> dict:
        """
        Expand a user query into structured academic search terms.

        Returns:
            {
                "primary_query": str,
                "synonyms": list[str],
                "technical_terms": list[str],
                "domain": str,
                "all_queries": list[str]   # primary + synonyms merged list
            }
        """
        if self._enabled:
            result = self._llm_expand(user_query)
            if result:
                result["all_queries"] = self._merge_queries(result)
                return result

        # Fallback: simple keyword extraction
        return self._simple_expand(user_query)

    def _llm_expand(self, query: str) -> dict | None:
        """Use LLaMA to expand query into structured search terms."""
        import json
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _EXPANSION_SYSTEM},
                    {"role": "user",   "content": f"Expand this research query: {query}"},
                ],
                temperature=0.1,
                max_tokens=300,
            )
            raw = resp.choices[0].message.content.strip()
            # Extract JSON even if surrounded by markdown
            if "```" in raw:
                raw = raw.split("```")[1].lstrip("json").strip()
            return json.loads(raw)
        except Exception as e:
            print(f"[QueryExpander] LLM expansion failed: {e}")
            return None

    def _simple_expand(self, query: str) -> dict:
        """Fallback: keyword extraction without LLM."""
        import re
        cleaned  = re.sub(r'[^\w\s]', ' ', query.lower())
        keywords = [t for t in cleaned.split()
                    if t not in self.STOP_WORDS and len(t) > 2]
        primary  = " ".join(keywords[:6])
        return {
            "primary_query":   primary or query,
            "synonyms":        [],
            "technical_terms": keywords,
            "domain":          "Computer Science",
            "all_queries":     [primary or query],
        }

    @staticmethod
    def _merge_queries(result: dict) -> list:
        """Combine primary query with top synonyms for multi-query fetching."""
        queries = [result.get("primary_query", "")]
        for syn in result.get("synonyms", [])[:2]:
            combined = f"{result.get('primary_query','')} {syn}".strip()
            if combined not in queries:
                queries.append(combined)
        return [q for q in queries if q]
