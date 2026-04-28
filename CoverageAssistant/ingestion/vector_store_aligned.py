import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
from langchain_ollama import ChatOllama

try:
    from .text_metadata_utils import normalize_text
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from text_metadata_utils import normalize_text

ROOT_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT_DIR / "processed_reports"
DB_PATH = str(ROOT_DIR / "pharma_db")
COLLECTION_NAME = "pharma_reports"

embedding_fn = OllamaEmbeddingFunction(
    model_name="nomic-embed-text",
    url="http://localhost:11434/api/embeddings",
)

_metadata_llm = ChatOllama(model="llama3.2", format="json", temperature=0)

_collection = None


def get_collection():
    """Return a cached handle to the pharma_reports collection."""
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=DB_PATH)
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_fn,
        )
    return _collection


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9-]+")
_ORDINAL_RE = re.compile(r"(\d+)(st|nd|rd|th)\b", re.IGNORECASE)
_DATE_FORMATS = (
    "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y",
    "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y",
    "%Y/%m/%d", "%d %B %Y", "%d %b %Y",
)


def _normalize_date(raw: str) -> str:
    """Normalize a free-form date string to YYYY-MM-DD. Returns 'Unknown' on failure.
    """
    if not raw or not isinstance(raw, str) or raw.strip().lower() == "unknown":
        return "Unknown"
    
    candidates = [s.strip() for s in raw.split(";") if s.strip()]
    candidates.append(raw.strip())  # also try the whole string as-is

    for candidate in candidates:
        cleaned = _ORDINAL_RE.sub(r"\1", candidate).strip().rstrip(",")
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return "Unknown"


def _entity_keywords(name: str, min_len: int = 4) -> list:
    """Lowercase tokens from a drug/company name suitable for substring search.
    """
    return [tok.lower() for tok in _TOKEN_RE.findall(name) if len(tok) >= min_len]


def _entities_mentioned_in(chunk_lower: str, entity_list: list) -> list:
    """Return the subset of entity_list whose primary keyword appears in chunk_lower."""
    matched = []
    for entity in entity_list:
        for kw in _entity_keywords(entity):
            if kw in chunk_lower:
                matched.append(entity)
                break
    return matched


def _normalize_meta(data: dict) -> dict:
    """Coerce LLM output to the canonical metadata shape (lists + joined strings)."""
    drugs = data.get("drug_names") or ["Unknown"]
    companies = data.get("company_names") or ["Unknown"]
    if not isinstance(drugs, list):
        drugs = [str(drugs)]
    if not isinstance(companies, list):
        companies = [str(companies)]
    drugs = [str(d).strip() for d in drugs if str(d).strip()]
    companies = [str(c).strip() for c in companies if str(c).strip()]
    if not drugs:
        drugs = ["Unknown"]
    if not companies:
        companies = ["Unknown"]
    return {
        "drug_names": drugs,
        "company_names": companies,
        "drug_name": ", ".join(drugs),
        "company_name": ", ".join(companies),
        "report_date": _normalize_date(str(data.get("report_date", "Unknown"))),
    }


def _invoke_llm(prompt: str) -> dict:
    response = _metadata_llm.invoke(prompt)
    return json.loads(response.content)


def extract_metadata_with_ai(text_content: str) -> dict:
    """Extract company/drug/date from the report text via the LLM.

    Returns a dict with both list and joined-string forms:
      drug_names: list[str], drug_name: str (comma-joined),
      company_names: list[str], company_name: str (comma-joined),
      report_date: str (YYYY-MM-DD or "Unknown").
    """
    snippet = text_content[:1500]
    prompt = f"""
    Analyze the clinical report text. Extract the following into a JSON object:
    - company_names: List of strings (e.g., ["Eli Lilly", "Pfizer"])
    - drug_names: List of strings (e.g., ["Lebrikizumab", "Dupixent"])
    - report_date: String in YYYY-MM-DD format (e.g., "2026-02-10")

    PRIORITY: If the text contains lines like "Company:", "Drug:", or "Date:",
    USE THOSE VALUES VERBATIM (but reformat the date to YYYY-MM-DD).

    For drug_names, list every distinct drug discussed in the report.
    For company_names, list every distinct company discussed.

    The report_date must come from the document content (e.g. a "Date:" line
    or publication date in the body). Do NOT infer the date from any filename
    or external source. Convert dates like "February 10, 2026" -> "2026-02-10"
    and "Nov 6th, 2025" -> "2025-11-06".

    If any field is missing, return ["Unknown"] for lists or "Unknown" for date.
    Output ONLY valid JSON.

    Text:
    {snippet}
    """

    try:
        result = _normalize_meta(_invoke_llm(prompt))
        if (result["drug_names"] == ["Unknown"]
                and result["company_names"] == ["Unknown"]
                and result["report_date"] == "Unknown"):
            raise ValueError("LLM returned all-Unknown")
        return result
    except Exception as e:
        print(f"  ⚠️  Metadata extraction attempt 1 failed: {e}; retrying...")
        try:
            return _normalize_meta(_invoke_llm(prompt))
        except Exception as e2:
            print(f"  ⚠️  Metadata extraction failed after retry: {e2}")
            return {
                "drug_names": ["Unknown"],
                "company_names": ["Unknown"],
                "drug_name": "Unknown",
                "company_name": "Unknown",
                "report_date": "Unknown",
            }


def chunk_text(text, chunk_size=1000, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        chunk = text[start:start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def _index_markdown_file(collection, md_path: Path) -> int:
    """Read, dedupe, chunk, embed, and add a single markdown file.
    """
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = normalize_text(content)

    if not content.strip():
        print(f"  ⚠️ Skipping empty: {md_path.name}")
        return 0

    doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]

    existing_by_source = collection.get(where={"source": md_path.name})
    if existing_by_source["ids"]:
        print(f"  ♻️ Refreshing existing source rows for: {md_path.name}")
        collection.delete(where={"source": md_path.name})

    existing_by_doc_id = collection.get(where={"doc_id": doc_id})
    if existing_by_doc_id["ids"]:
        print(f"  ♻️ Refreshing existing doc_id rows for: {doc_id}")
        collection.delete(where={"doc_id": doc_id})

    print(f"  🧠 AI extracting metadata from {md_path.name}...")
    ai_meta = extract_metadata_with_ai(content)

    drug_list = ai_meta["drug_names"]
    company_list = ai_meta["company_names"]

    chunks = chunk_text(content)
    timestamp = datetime.utcnow().isoformat()

    ids, documents, metadatas = [], [], []

    for i, chunk in enumerate(chunks):
        chunk_lower = chunk.lower()
        chunk_drugs = _entities_mentioned_in(chunk_lower, drug_list) or drug_list
        chunk_companies = _entities_mentioned_in(chunk_lower, company_list) or company_list

        for j, drug in enumerate(chunk_drugs):
            for k, company in enumerate(chunk_companies):
                ids.append(f"{doc_id}_chunk_{i}_d{j}_c{k}")
                documents.append(chunk)
                metadatas.append({
                    "doc_id": doc_id,
                    "source": md_path.name,
                    "chunk_index": i,
                    "uploaded_at": timestamp,
                    "file_type": "markdown",
                    "company_name": company,
                    "drug_name": drug,
                    "report_date": ai_meta["report_date"],
                })

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    print(
        f"  ✅ {md_path.name}: {len(chunks)} chunks → {len(ids)} rows"
        f" — drugs={drug_list}, companies={company_list}, date={ai_meta['report_date']!r}"
    )
    return len(ids)


def index_single_markdown(md_path: Path) -> int:
    """Per-upload entry point: index one markdown file into pharma_db."""
    return _index_markdown_file(get_collection(), Path(md_path))


def index_processed_data():
    """Batch entry point: index every .md in processed_reports/ into pharma_db."""
    md_files = list(PROCESSED_DIR.glob("*.md"))
    if not md_files:
        print(f"No .md files found in {PROCESSED_DIR}")
        return

    collection = get_collection()
    total = 0
    for md_path in md_files:
        total += _index_markdown_file(collection, md_path)

    print(f"--- Indexed {total} total chunks into {DB_PATH} ---")


if __name__ == "__main__":
    index_processed_data()
