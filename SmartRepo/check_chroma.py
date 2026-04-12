from pathlib import Path
import chromadb

BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "chroma_store"

client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = client.get_or_create_collection(name="reports")

count = collection.count()
print(f"Chroma path: {CHROMA_DIR}")
print(f"Collection name: reports")
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