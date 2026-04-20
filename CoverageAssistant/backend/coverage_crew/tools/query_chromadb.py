import re
import chromadb
from typing import Type, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime, timedelta

repo_root = Path(__file__).resolve().parents[4]
CHROMA_PATH = str(repo_root / "SmartRepo" / "chroma_store")

_STOP_WORDS = {
    "a", "an", "the", "in", "of", "to", "and", "or", "is", "was", "were",
    "for", "with", "that", "this", "it", "as", "at", "by", "from", "on",
    "are", "be", "been", "has", "have", "had", "not", "but", "its", "their",
}


_BULLET_PATTERN = re.compile(r'[\u25cf\u25cb\u2022\u2013\u2014●•–—]\s*')


class QueryDBToolInput(BaseModel):
    """Input schema for QueryDBTool."""
    claim_text: str = Field(..., description="The claim text to search for similar historical claims in ChromaDB")
    drug_name: Optional[str] = Field(None, description="Drug name keyword to filter by matching source filenames (e.g. 'Lebrikizumab')")
    company_name: Optional[str] = Field(None, description="Company name keyword to filter by matching source filenames (e.g. 'Eli Lilly')")


class QueryDBTool(BaseTool):
    name: str = "Query ChromaDB"
    description: str = (
        "Searches ChromaDB for similar historical claims. "
        "Input: claim_text (string) — the claim sentence to search for. "
        'Example: {"claim_text": str}'
    )
    args_schema: Type[BaseModel] = QueryDBToolInput

    @staticmethod
    def _keywords(name: str) -> list:

        return [w.lower() for w in name.split() if len(w) > 3]

    def _extract_best_sentence(self, chunk: str, claim: str) -> str:

        flat = _BULLET_PATTERN.sub('', chunk)
        flat = re.sub(r'\s+', ' ', flat).strip()

        sentences = re.split(r'(?<=[.!?])\s+', flat)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

        if not sentences:
            return flat[:250]

        claim_lower = claim.lower().strip()

        for sentence in sentences:
            s_lower = sentence.lower()
            if claim_lower in s_lower or s_lower in claim_lower:
                return sentence

        claim_words = set(claim_lower.split()) - _STOP_WORDS
        best = max(
            sentences,
            key=lambda s: len(claim_words & (set(s.lower().split()) - _STOP_WORDS))
        )
        return best

    def _run(
        self,
        claim_text: str,
        drug_name: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> str:
        print(f"CALLING QueryDBTool WITH:\n  claim  : {claim_text}")
        if drug_name:
            print(f"  drug   : {drug_name}")
        if company_name:
            print(f"  company: {company_name}")

        try:
            client = chromadb.PersistentClient(path=CHROMA_PATH)
            collection = client.get_collection("reports")

            source_condition = None
            drug_keywords = self._keywords(drug_name) if drug_name else []
            company_keywords = self._keywords(company_name) if company_name else []
            all_keywords = drug_keywords + company_keywords

            if all_keywords:
                all_meta = collection.get(include=["metadatas"])
                matching_sources = list(dict.fromkeys(
                    m["source"]
                    for m in all_meta["metadatas"]
                    if m.get("source")
                    and any(kw in m["source"].lower() for kw in all_keywords)
                ))
                if matching_sources:
                    source_condition = {"source": {"$in": matching_sources}}
                    print(f"  matched sources: {matching_sources}")
                else:
                    print("  no sources matched drug/company keywords; using full collection")

            cutoff_ts = int((datetime.utcnow() - timedelta(days=30)).timestamp())
            date_condition = {"report_date_ts": {"$gte": cutoff_ts}}

            where_attempts = []
            if source_condition:
                where_attempts.append({"$and": [date_condition, source_condition]})
                where_attempts.append(source_condition)
            else:
                where_attempts.append(date_condition)
            where_attempts.append(None)

            results = None
            for where in where_attempts:
                try:
                    query_kwargs = {"query_texts": [claim_text], "n_results": 3}
                    if where is not None:
                        query_kwargs["where"] = where
                    results = collection.query(**query_kwargs)
                    label = "no filter" if where is None else str(where)
                    print(f"  query succeeded with: {label}")
                    break
                except Exception as e:
                    print(f"  filter failed ({e}); trying next fallback")

            if results is None:
                return "No historical matches found"

            docs = results["documents"][0] if results["documents"] else []
            if not docs:
                return "No historical matches found"

            best_sentence = self._extract_best_sentence(docs[0], claim_text)
            print(f"  returning: {best_sentence}")
            return best_sentence

        except Exception as e:
            return f"Error querying ChromaDB: {str(e)}"
