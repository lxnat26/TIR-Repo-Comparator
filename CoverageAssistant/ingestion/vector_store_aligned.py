"""Indexes parsed markdown reports into the unified pharma_db/pharma_reports collection.

Metadata (company_name, drug_name, report_date) is extracted by an LLM
(llama3.2 via Ollama, JSON mode) — this handles varied header formats.
"""

import hashlib
import json
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

# LLM for metadata extraction — JSON-mode output for reliable parsing.
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


def extract_metadata_with_ai(text_content: str) -> dict:
    """Dynamically extracts metadata as joined strings to handle multiple entries."""
    snippet = text_content[:1500]
    prompt = f"""
    Analyze the clinical report text. Extract the following into a JSON object:
    - company_names: List of strings (e.g., ["Eli Lilly", "Pfizer"])
    - drug_names: List of strings (e.g., ["Lebrikizumab", "Dupixent"])
    - report_date: String in YYYY-MM-DD format
    
    If any field is missing, return ["Unknown"] for lists or "Unknown" for date.

    Text:
    {snippet}
    """
    try:
        response = _metadata_llm.invoke(prompt)
        data = json.loads(response.content)
        # Flatten lists into comma-separated strings for ChromaDB compatibility
        return {
            "company_name": ", ".join(data.get("company_names", ["Unknown"])),
            "drug_name": ", ".join(data.get("drug_names", ["Unknown"])),
            "report_date": str(data.get("report_date", "Unknown"))
        }
    except Exception as e:
        print(f"  ⚠️  Metadata extraction failed: {e}")
        return {
            "company_name": "Unknown",
            "drug_name": "Unknown",
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
    """Read, dedupe, chunk, embed, and add a single markdown file."""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = normalize_text(content)

    if not content.strip():
        print(f"  ⚠️ Skipping empty: {md_path.name}")
        return 0

    doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]
    existing = collection.get(where={"doc_id": doc_id})
    if existing["ids"]:
        print(f"  ⏭️ Already indexed: {md_path.name}")
        return 0

    print(f"  🧠 AI extracting metadata from {md_path.name}...")
    ai_meta = extract_metadata_with_ai(content)

    chunks = chunk_text(content)
    timestamp = datetime.utcnow().isoformat()

    ids, documents, metadatas = [], [], []

    for i, chunk in enumerate(chunks):
        ids.append(f"{doc_id}_chunk_{i}")
        documents.append(chunk)
        metadatas.append({
            "doc_id": doc_id,
            "source": md_path.name,
            "chunk_index": i,
            "uploaded_at": timestamp,
            "file_type": "markdown",
            "company_name": ai_meta["company_name"],
            "drug_name": ai_meta["drug_name"],
            "report_date": ai_meta["report_date"],
        })

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    print(
        f"  ✅ {md_path.name}: {len(chunks)} chunks"
        f" — company={ai_meta['company_name']!r}, drug={ai_meta['drug_name']!r}, date={ai_meta['report_date']!r}"
    )
    return len(chunks)


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