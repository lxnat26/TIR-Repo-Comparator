"""Inspector: dump contents of the unified pharma_db/pharma_reports collection."""
from pathlib import Path
import chromadb

REPO_ROOT = Path(__file__).resolve().parents[1]
CHROMA_DIR = REPO_ROOT / "pharma_db"
COLLECTION_NAME = "pharma_reports"

client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = client.get_or_create_collection(name=COLLECTION_NAME)

count = collection.count()
print(f"Chroma path: {CHROMA_DIR}")
print(f"Collection name: {COLLECTION_NAME}")
print(f"Total items stored: {count}")

if count > 0:
    data = collection.get(include=["documents", "metadatas"])
    print("\nStored items:")
    for i, doc_id in enumerate(data["ids"]):
        meta = data["metadatas"][i] if data["metadatas"] else {}
        doc = data["documents"][i] if data["documents"] else ""
        print(f"\nID: {doc_id}")
        print(f"Metadata: {meta}")
        print(f"Preview: {doc[:300].replace(chr(10), ' ')}")
else:
    print("No items found in the collection.")
