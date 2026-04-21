import re
from typing import Type, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from pathlib import Path
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

repo_root = Path(__file__).resolve().parents[4]
PHARMA_DB_PATH = str(repo_root / "pharma_db")
COLLECTION_NAME = "pharma_reports"

_BULLET_PATTERN = re.compile(r'[\u25cf\u25cb\u2022\u2013\u2014●•–—]\s*')


class QueryDBToolInput(BaseModel):
    """Input schema for QueryDBTool."""
    claim_text: str = Field(..., description="The claim text to search for similar historical claims in ChromaDB")
    drug_name: Optional[str] = Field(None, description="Drug name keyword to filter results (e.g. 'Lebrikizumab')")
    company_name: Optional[str] = Field(None, description="Company name keyword to filter results (e.g. 'Eli Lilly')")


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
        """
        Split a name into individual lowercase keywords longer than 3 chars.
        Handles multi-word names like 'Eli Lilly' → ['lilly']
        or 'Lebrikizumab' → ['lebrikizumab'].
        """
        return [w.lower() for w in name.split() if len(w) > 3]

    def _extract_best_sentence(self, chunk: str, claim: str) -> str:
        """
        Return the single sentence from a raw chunk that best matches the claim.
        """
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

        claim_words = set(claim_lower.split())
        best = max(
            sentences,
            key=lambda s: len(claim_words & set(s.lower().split()))
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

            embeddings = OllamaEmbeddings(model="nomic-embed-text")
            vector_store = Chroma(
                collection_name=COLLECTION_NAME,
                persist_directory=PHARMA_DB_PATH,
                embedding_function=embeddings,
            )

            drug_keywords = self._keywords(drug_name) if drug_name else []
            company_keywords = self._keywords(company_name) if company_name else []
            all_keywords = drug_keywords + company_keywords

            chroma_filter = None
            if all_keywords:
                raw = vector_store._collection.get(include=["metadatas"])
                matched_companies = set()
                matched_drugs = set()
                for meta in raw["metadatas"]:
                    company_val = (meta.get("company_name") or "").lower()
                    drug_val = (meta.get("drug_name") or "").lower()
                    for kw in all_keywords:
                        if kw in company_val:
                            matched_companies.add(meta["company_name"])
                        if kw in drug_val:
                            matched_drugs.add(meta["drug_name"])

                conditions = []
                if matched_companies:
                    if len(matched_companies) == 1:
                        conditions.append({"company_name": {"$eq": next(iter(matched_companies))}})
                    else:
                        conditions.append({"company_name": {"$in": list(matched_companies)}})
                if matched_drugs:
                    if len(matched_drugs) == 1:
                        conditions.append({"drug_name": {"$eq": next(iter(matched_drugs))}})
                    else:
                        conditions.append({"drug_name": {"$in": list(matched_drugs)}})

                if conditions:
                    chroma_filter = {"$or": conditions} if len(conditions) > 1 else conditions[0]
                    print(f"  metadata filter: {chroma_filter}")
                else:
                    print("  no metadata matched drug/company keywords; using full collection")
            docs = []
            attempts = [chroma_filter, None] if chroma_filter else [None]

            for attempt_filter in attempts:
                label = str(attempt_filter) if attempt_filter else "no filter"
                results = vector_store.similarity_search(
                    claim_text, k=3, filter=attempt_filter
                )
                if results:
                    print(f"  query returned {len(results)} results with: {label}")
                    docs = [doc.page_content for doc in results]
                    break
                else:
                    print(f"  query empty with: {label}; trying next fallback")

            if not docs:
                return "No historical matches found"

            best_sentence = self._extract_best_sentence(docs[0], claim_text)
            print(f"  returning: {best_sentence}")
            return best_sentence

        except Exception as e:
            return f"Error querying ChromaDB: {str(e)}"
