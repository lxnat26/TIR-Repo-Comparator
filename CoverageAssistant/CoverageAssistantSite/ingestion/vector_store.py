import hashlib
from pathlib import Path
from datetime import datetime
import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

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
    """ENTRY POINT — called by data_main.py"""
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

        if not content.strip():
            print(f"  ⚠️  Skipping empty: {md_path.name}")
            continue

        doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        existing = collection.get(where={"doc_id": doc_id})
        if existing["ids"]:
            print(f"  ⏭️  Already indexed: {md_path.name}")
            continue

        chunks = chunk_text(content)
        timestamp = datetime.utcnow().isoformat()

        # Extract basic metadata from filename (no LLM needed)
        stem = md_path.stem  # e.g. "2024_lilly_lebrikizumab_phase2_update"
        parts = stem.split("_")
        report_date = parts[0] if parts[0].isdigit() else "Unknown"
        company_name = parts[1].capitalize() if len(parts) > 1 else "Unknown"
        drug_name = parts[2].capitalize() if len(parts) > 2 else "Unknown"

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
                "company_name": company_name,
                "drug_name": drug_name,
                "report_date": report_date,
            })

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"  ✅ {md_path.name}: {len(chunks)} chunks")
        total += len(chunks)

    print(f"--- Indexed {total} total chunks into {DB_PATH} ---")


if __name__ == "__main__":
    index_processed_data()