from pathlib import Path
import chromadb
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
CHROMA_DIR = BASE_DIR / "chroma_store"

client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = client.get_or_create_collection(name="reports")

pdf_files = sorted(DOCS_DIR.glob("*.pdf"))

if not pdf_files:
    print("No PDF files found in SmartRepo/docs")
    raise SystemExit

for pdf in pdf_files:
    reader = PdfReader(str(pdf))
    text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()

    if not text:
        print(f"Skipped {pdf.name}: no extractable text")
        continue

    collection.upsert(
        ids=[pdf.stem],
        documents=[text],
        metadatas=[{"source": pdf.name}]
    )
    print(f"Stored: {pdf.name}")

print(f"\nDone. Total items now: {collection.count()}")