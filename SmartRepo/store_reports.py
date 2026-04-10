from pathlib import Path
from datetime import datetime
import hashlib
import chromadb
from chromadb.config import Settings
from pypdf import PdfReader


CHROMA_PATH = "SmartRepo/chroma_store"
DOCS_PATH = "SmartRepo/docs"


client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection("reports")


def make_doc_id(file_bytes, filename):
    digest = hashlib.sha256(file_bytes).hexdigest()[:16]
    safe_name = Path(filename).stem.replace(" ", "_")
    return f"{safe_name}_{digest}"


def extract_pdf_text(file_path):
    reader = PdfReader(file_path)
    pages = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append((i + 1, text))

    return pages


def chunk_text(text, chunk_size=800, overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        chunk = text[start:start + chunk_size]
        chunks.append(chunk.strip())
        start += chunk_size - overlap

    return chunks


def ingest_pdf(file_path):

    file_path = Path(file_path)

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    doc_id = make_doc_id(file_bytes, file_path.name)

    existing = collection.get(where={"doc_id": doc_id})

    if existing["ids"]:
        print(f"Already stored: {doc_id}")
        return

    pages = extract_pdf_text(file_path)

    ids = []
    documents = []
    metadatas = []

    timestamp = datetime.utcnow().isoformat()

    chunk_index = 0

    for page_num, page_text in pages:

        chunks = chunk_text(page_text)

        for chunk in chunks:

            chunk_id = f"{doc_id}_chunk_{chunk_index}"

            ids.append(chunk_id)
            documents.append(chunk)

            metadatas.append({

                "doc_id": doc_id,
                "source": str(file_path),
                "page": page_num,
                "chunk_index": chunk_index,
                "uploaded_at": timestamp,
                "file_type": "pdf"

            })

            chunk_index += 1

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

    print(f"Inserted {len(ids)} chunks for {doc_id}")
def ingest_all_docs():

    docs_folder = Path(DOCS_PATH)

    for file in docs_folder.glob("*.pdf"):
        print("Processing:", file.name)
        ingest_pdf(file)


if __name__ == "__main__":
    ingest_all_docs()