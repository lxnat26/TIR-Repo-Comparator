import re
from datetime import datetime
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
_TOKEN_RE = re.compile(r'[A-Za-z][A-Za-z0-9-]+')
_MAX_SENTENCE_CHARS = 300
_DENSE_WINDOW_CHARS = 240


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
        Extract lowercase alphanumeric tokens (>=4 chars) from a name.

        Strips parens/commas/semicolons so that multi-entity inputs like
        "Sonrotoclax (BCL2i), Zanubrutinib, Venetoclax" yield clean tokens
        ['sonrotoclax', 'bcl2i', 'zanubrutinib', 'venetoclax'] instead of
        the punctuation-trailing ['sonrotoclax', '(bcl2i),', 'zanubrutinib,', ...]
        that whitespace-splitting produced — those wouldn't substring-match
        per-drug metadata values like 'Zanubrutinib'.
        """
        return [tok.lower() for tok in _TOKEN_RE.findall(name) if len(tok) >= 4]

    @staticmethod
    def _split_entities(raw: Optional[str]) -> list[str]:
        """
        Split a metadata string into entity candidates.

        Metadata usually arrives as a comma-joined list like
        "Jaypirca, Venetoclax, Acalabrutinib". We keep multi-word entities
        intact while splitting on top-level commas/semicolons/slashes.
        """
        if not raw:
            return []
        parts = re.split(r"\s*[;,/]\s*", raw)
        return [part.strip() for part in parts if part.strip()]

    def _select_claim_entities(self, claim_text: str, raw_entities: Optional[str]) -> list[str]:
        """
        Narrow document-level metadata to the entities explicitly mentioned
        in the claim text. If there is only one entity overall, keep it.
        If nothing is mentioned explicitly, fall back to the first entity as
        the document's primary focus instead of dropping the filter entirely.
        """
        entities = self._split_entities(raw_entities)
        if len(entities) <= 1:
            return entities

        claim_lower = claim_text.lower()
        matched = []
        for entity in entities:
            kws = self._keywords(entity)
            if kws and any(kw in claim_lower for kw in kws):
                matched.append(entity)
        if matched:
            return matched
        return entities[:1]

    def _extract_best_sentence(self, chunk: str, claim: str, drug_focus: str = "") -> str:
        cleaned = _BULLET_PATTERN.sub('', chunk)

        candidates = []
        for line in cleaned.split('\n'):
            line = line.strip()
            if not line:
                continue
            for piece in re.split(r'(?<=[.!?])\s+', line):
                piece = re.sub(r'\s+', ' ', piece).strip()
                if len(piece) >= 15:
                    candidates.append(piece)

        if not candidates:
            return re.sub(r'\s+', ' ', cleaned).strip()[:_DENSE_WINDOW_CHARS]

        claim_lower = claim.lower().strip()

        for cand in candidates:
            c_lower = cand.lower()
            if claim_lower in c_lower or c_lower in claim_lower:
                if len(cand) > _MAX_SENTENCE_CHARS:
                    return self._extract_dense_window(cand, claim, drug_focus)
                return cand

        if drug_focus:
            focus_kws = self._keywords(drug_focus)
            focused = [c for c in candidates if any(kw in c.lower() for kw in focus_kws)]
            if focused:
                candidates = focused

        claim_words = set(_TOKEN_RE.findall(claim_lower))
        if not claim_words:
            return min(candidates, key=len)

        def _score(s):
            s_words = set(_TOKEN_RE.findall(s.lower()))
            return (len(claim_words & s_words), -len(s))

        best = max(candidates, key=_score)
        if len(best) > _MAX_SENTENCE_CHARS:
            return self._extract_dense_window(best, claim, drug_focus)
        return best

    def _extract_dense_window(self, text: str, claim: str, drug_focus: str = "") -> str:
        """
        For run-on text without sentence punctuation, return the ~240-char
        window centered on the highest concentration of claim/drug keywords.
        Window is trimmed to whitespace boundaries so we don't cut mid-word.
        """
        claim_lower = claim.lower()
        text_lower = text.lower()

        # Build the keyword set: claim tokens (>=4 chars) + drug-focus tokens.
        keywords = {tok for tok in _TOKEN_RE.findall(claim_lower) if len(tok) >= 4}
        if drug_focus:
            keywords.update(self._keywords(drug_focus))
        if not keywords:
            return text[:_DENSE_WINDOW_CHARS]

        # All hit positions of any keyword in the text.
        hits = []
        for kw in keywords:
            start = 0
            while True:
                idx = text_lower.find(kw, start)
                if idx == -1:
                    break
                hits.append(idx)
                start = idx + len(kw)
        if not hits:
            return text[:_DENSE_WINDOW_CHARS]

        half = _DENSE_WINDOW_CHARS // 2
        best_center = hits[0]
        best_density = 0
        for center in hits:
            lo, hi = center - half, center + half
            density = sum(1 for h in hits if lo <= h <= hi)
            if density > best_density:
                best_density = density
                best_center = center

        lo = max(0, best_center - half)
        hi = min(len(text), best_center + half)
        while lo > 0 and not text[lo - 1].isspace():
            lo -= 1
        while hi < len(text) and not text[hi].isspace():
            hi += 1
        return text[lo:hi].strip()

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
            focused_drugs = self._select_claim_entities(claim_text, drug_name)
            focused_companies = self._select_claim_entities(claim_text, company_name)

            effective_drug_name = ", ".join(focused_drugs) if focused_drugs else None
            effective_company_name = ", ".join(focused_companies) if focused_companies else None

            if effective_drug_name and effective_drug_name != drug_name:
                print(f"  focused drug metadata   : {effective_drug_name}")
            if effective_company_name and effective_company_name != company_name:
                print(f"  focused company metadata: {effective_company_name}")

            embeddings = OllamaEmbeddings(model="nomic-embed-text")
            vector_store = Chroma(
                collection_name=COLLECTION_NAME,
                persist_directory=PHARMA_DB_PATH,
                embedding_function=embeddings,
            )

            drug_keywords = self._keywords(effective_drug_name) if effective_drug_name else []
            company_keywords = self._keywords(effective_company_name) if effective_company_name else []

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

                if effective_drug_name and not matched_drugs:
                    print("  drug was specified but no chunk has that drug; "
                          "refusing company-only fallback — returning no match")
                    return {"text": "No historical matches found", "report_date": "Unknown"}

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
            if (effective_drug_name or effective_company_name) and drug_company_filter is None:
                print("  caller specified drug/company but no matching chunks exist; "
                      "returning no match (refusing to fall back to unfiltered search)")
                return {"text": "No historical matches found", "report_date": "Unknown"}

            query_parts = []
            if effective_drug_name:
                query_parts.append(effective_drug_name)
            if effective_company_name:
                query_parts.append(effective_company_name)
            query_parts.append(claim_text)
            enriched_query = " ".join(query_parts)

            MIN_RELEVANCE = 0.5

            winner = None
            winner_score = None

            attempts = [drug_company_filter] if drug_company_filter else [None]

            for attempt_filter in attempts:
                label = str(attempt_filter) if attempt_filter else "no filter"

                scored_raw = vector_store.similarity_search_with_relevance_scores(
                    enriched_query, k=20, filter=attempt_filter
                )
                if not scored_raw:
                    print(f"  query empty with: {label}; trying next fallback")
                    continue


                seen_chunks = {}
                for doc, score in scored_raw:
                    meta = doc.metadata or {}
                    key = (meta.get("source"), meta.get("chunk_index"))
                    if key not in seen_chunks or seen_chunks[key][1] < score:
                        seen_chunks[key] = (doc, score)
                scored = sorted(seen_chunks.values(), key=lambda ds: ds[1], reverse=True)
                scope = "all dates"

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

            winner_drug = (winner.metadata or {}).get("drug_name", "") if winner.metadata else ""
            best_sentence = self._extract_best_sentence(
                winner.page_content, claim_text, drug_focus=winner_drug
            )
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
