import chromadb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "chroma_store"

client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = client.get_or_create_collection(name="reports_test")

collection.add(
    ids=["report1", "report2"],
    documents=[
        "This is a sample report about a Phase 2 trial update.",
        "This is another sample report about safety findings."
    ],
    metadatas=[
        {"source": "sample1"},
        {"source": "sample2"}
    ]
)

print("Chroma is running.")
print("Data stored in collection: reports_test")
print(f"Persisted at: {CHROMA_DIR}")