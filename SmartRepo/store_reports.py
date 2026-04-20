from pathlib import Path
from datetime import datetime
import hashlib
import re
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


def extract_field(text: str, field: str) -> str:
    """
    Extract a named field from report header text that looks like:
      'Company:  Eli  Lilly'
      'Drug:\n \nLebrikizumab\n \n(Ebglyss)'
    Returns the raw value (may contain extra whitespace — caller should normalize).
    Returns empty string if not found.
    """
    pattern = re.compile(
        rf'{re.escape(field)}:\s*([\w()\-\/\s]+?)(?=\n\s*\n|\n\s*[A-Z][a-z]+:|\Z)',
        re.IGNORECASE | re.DOTALL
    )
    match = pattern.search(text)
    if match:
        return re.sub(r'\s+', ' ', match.group(1)).strip()
    return ""


def extract_report_date_ts(text: str) -> int:
    """
    Parse the publication date written inside the report text and return it
    as a Unix timestamp (int) so ChromaDB's $gte/$lte operators can filter it.

    Handles PDF-extracted text with extra whitespace/newlines between tokens,
    e.g. 'Date:\n \nSeptember\n \n21,\n \n2024'.

    Looks for patterns like:
      'Date: September 21, 2024'
      'Date: July 10, 2025'
      'Date: March 2024'
    Falls back to the current time if no date is found.
    """
    formats = ["%B %d %Y", "%B %Y"]
    # \s+ handles newlines and multiple spaces between PDF-extracted tokens
    match = re.search(
        r'Date:\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4}|[A-Za-z]+\s+\d{4})',
        text
    )
    if match:
        # Collapse all internal whitespace and strip commas
        raw = re.sub(r'\s+', ' ', match.group(1)).replace(",", "").strip()
        for fmt in formats:
            try:
                return int(datetime.strptime(raw, fmt).timestamp())
            except ValueError:
                continue
    return int(datetime.utcnow().timestamp())


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

    # Extract metadata from the first page text.
    # report_date_ts is stored as a Unix timestamp int so ChromaDB's $gte
    # operator can filter by report date (not upload date).
    # company_name and drug_name are stored for source-keyword filtering
    # in QueryDBTool, eliminating the need for a separate pharma_db store.
    first_page_text = pages[0][1] if pages else ""
    report_date_ts = extract_report_date_ts(first_page_text)
    company_name = extract_field(first_page_text, "Company")
    drug_name = extract_field(first_page_text, "Drug")

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
                "report_date_ts": report_date_ts,
                "company_name": company_name,
                "drug_name": drug_name,
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