import hashlib
from pathlib import Path
from datetime import datetime
import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

from text_metadata_utils import (
    normalize_text,
    extract_field,
    extract_report_date,
    extract_report_date_ts,
)

ROOT_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT_DIR / "processed_reports"
DB_PATH = str(ROOT_DIR / "pharma_db")
COLLECTION_NAME = "pharma_reports"

embedding_fn = OllamaEmbeddingFunction(
    model_name="nomic-embed-text",
    url="http://localhost:11434/api/embeddings",
)


def chunk_text(text, chunk_size=1000, overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        chunk = text[start:start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def index_processed_data():
    """Indexes cleaned markdown into pharma_db with aligned metadata extraction."""
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
    )

    md_files = list(PROCESSED_DIR.glob("*.md"))
    if not md_files:
        print(f"No .md files found in {PROCESSED_DIR}")
        return

    total = 0

    for md_path in md_files:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        content = normalize_text(content)

        if not content.strip():
            print(f"  ⚠️ Skipping empty: {md_path.name}")
            continue

        doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        existing = collection.get(where={"doc_id": doc_id})
        if existing["ids"]:
            print(f"  ⏭️ Already indexed: {md_path.name}")
            continue

        # Use the beginning of the doc for metadata extraction
        header_text = content[:3000]

        company_name = extract_field(header_text, "Company") or "Unknown"
        drug_name = extract_field(header_text, "Drug") or "Unknown"
        report_date = extract_report_date(header_text)
        report_date_ts = extract_report_date_ts(header_text)

        chunks = chunk_text(content)
        timestamp = datetime.utcnow().isoformat()

        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            ids.append(f"{doc_id}_chunk_{i}")
            documents.append(chunk)
            metadatas.append({
                "doc_id": doc_id,
                "source": md_path.name,
                "chunk_index": i,
                "uploaded_at": timestamp,
                "file_type": "markdown",
                "company_name": company_name,
                "drug_name": drug_name,
                "report_date": report_date,
                "report_date_ts": report_date_ts,
            })

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"  ✅ {md_path.name}: {len(chunks)} chunks")
        total += len(chunks)

    print(f"--- Indexed {total} total chunks into {DB_PATH} ---")


if __name__ == "__main__":
    index_processed_data()