import re
from datetime import datetime, timedelta, timezone
from typing import Type, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from pathlib import Path
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

repo_root = Path(__file__).resolve().parents[4]
PHARMA_DB_PATH = str(repo_root / "pharma_db")
COLLECTION_NAME = "pharma_reports"

DATE_WINDOW_DAYS = 180

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

    def search_with_metadata(
        self,
        claim_text: str,
        drug_name: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> dict:

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

            drug_company_filter = None
            if drug_keywords or company_keywords:
                raw = vector_store._collection.get(include=["metadatas"])
                matched_companies = set()
                matched_drugs = set()
                for meta in raw["metadatas"]:
                    company_val = (meta.get("company_name") or "").lower()
                    drug_val = (meta.get("drug_name") or "").lower()

                    for kw in drug_keywords:
                        if kw in drug_val:
                            matched_drugs.add(meta["drug_name"])
                    for kw in company_keywords:
                        if kw in company_val:
                            matched_companies.add(meta["company_name"])

                conditions = []
                if matched_drugs:
                    if len(matched_drugs) == 1:
                        conditions.append({"drug_name": {"$eq": next(iter(matched_drugs))}})
                    else:
                        conditions.append({"drug_name": {"$in": list(matched_drugs)}})
                if matched_companies:
                    if len(matched_companies) == 1:
                        conditions.append({"company_name": {"$eq": next(iter(matched_companies))}})
                    else:
                        conditions.append({"company_name": {"$in": list(matched_companies)}})

                if conditions:
 
                    drug_company_filter = (
                        {"$and": conditions} if len(conditions) > 1 else conditions[0]
                    )
                    print(f"  drug/company filter: {drug_company_filter}")
                else:
                    print("  no metadata matched drug/company keywords")
            if (drug_name or company_name) and drug_company_filter is None:
                print("  caller specified drug/company but no matching chunks exist; "
                      "returning no match (refusing to fall back to unfiltered search)")
                return {"text": "No historical matches found", "report_date": "Unknown"}

            today_date = datetime.now(timezone.utc).date()
            cutoff_date = today_date - timedelta(days=DATE_WINDOW_DAYS)
            today_iso = today_date.isoformat()
            cutoff_iso = cutoff_date.isoformat()
            print(f"  date window: report_date in [{cutoff_iso}, {today_iso}] "
                  f"({DATE_WINDOW_DAYS} days)")

            def in_window(meta) -> bool:
                """True iff meta.report_date is a real ISO date inside the window."""
                rd = ((meta or {}).get("report_date") or "")[:10]
                if len(rd) != 10:
                    return False
                try:
                    doc_date = datetime.strptime(rd, "%Y-%m-%d").date()
                except ValueError:
                    return False
                return cutoff_date <= doc_date <= today_date

            query_parts = []
            if drug_name:
                query_parts.append(drug_name)
            if company_name:
                query_parts.append(company_name)
            query_parts.append(claim_text)
            enriched_query = " ".join(query_parts)

            MIN_RELEVANCE = 0.5

            winner = None
            winner_score = None

            attempts = [drug_company_filter] if drug_company_filter else [None]

            for attempt_filter in attempts:
                label = str(attempt_filter) if attempt_filter else "no filter"

                scored_raw = vector_store.similarity_search_with_relevance_scores(
                    enriched_query, k=10, filter=attempt_filter
                )
                if not scored_raw:
                    print(f"  query empty with: {label}; trying next fallback")
                    continue


                in_window_scored = [(d, s) for d, s in scored_raw if in_window(d.metadata)]
                rejected = len(scored_raw) - len(in_window_scored)

                if in_window_scored:
                    scored = in_window_scored
                    scope = f"in-window [{cutoff_iso}, {today_iso}]"
                    if rejected:
                        print(f"  {rejected}/{len(scored_raw)} candidates dropped by "
                              f"date window [{cutoff_iso}, {today_iso}]")
                elif attempt_filter is not None:
   
                    scored = scored_raw
                    scope = "same drug, any date (no in-window history)"
                    print(f"  no in-window candidates for this drug; "
                          f"relaxing date window to include older same-drug history")
                else:
                   
                    print(f"  no in-window candidates with: {label}; "
                          f"trying next fallback")
                    continue

                display = scored[:3]
                print(f"  top-{len(display)} candidates ({scope}) with: {label}")
                for doc, score in display:
                    src = (doc.metadata or {}).get("source", "?")
                    rd = (doc.metadata or {}).get("report_date", "?")
                    preview = doc.page_content[:80].replace("\n", " ")
                    print(f"    score={score:.3f}  date={rd}  source={src}  "
                          f"content={preview!r}")

                best_doc, best_score = display[0]
                if best_score < MIN_RELEVANCE:
                    print(
                        f"  best score {best_score:.3f} < threshold {MIN_RELEVANCE}; "
                        f"treating as no match (with: {label})"
                    )
                    continue

                winner = best_doc
                winner_score = best_score
                break

            if winner is None:
                return {"text": "No historical matches found", "report_date": "Unknown"}

            best_sentence = self._extract_best_sentence(winner.page_content, claim_text)
            report_date = winner.metadata.get("report_date", "Unknown") if winner.metadata else "Unknown"
            print(f"  returning (score={winner_score:.3f}): {best_sentence}")
            print(f"  report_date: {report_date}")
            return {"text": best_sentence, "report_date": report_date}

        except Exception as e:
            return {"text": f"Error querying ChromaDB: {str(e)}", "report_date": "Unknown"}

    def _run(
        self,
        claim_text: str,
        drug_name: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> str:

        return self.search_with_metadata(claim_text, drug_name, company_name)["text"]
