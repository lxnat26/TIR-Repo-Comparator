from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from pathlib import Path

# Setup paths
ROOT_DIR = Path(__file__).resolve().parents[2]
db_path = str(ROOT_DIR / "pharma_db")
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# Connect to your existing database
vector_db = Chroma(
    persist_directory=db_path,
    embedding_function=embeddings,
    collection_name="pharma_reports"
)

# 1. Check the count
all_docs = vector_db.get()
print(f"📊 Total chunks in database: {len(all_docs['ids'])}")

# 2. Inspect the first 5 chunks
if len(all_docs['ids']) > 0:
    print("\n🔍 --- Sample Records ---")

    sample_size = min(5, len(all_docs['ids']))

    for i in range(sample_size):
        print(f"\n--- Sample {i+1} ---")

        print("\nMetadata:")
        print(all_docs['metadatas'][i])

        print("\nText Snippet:")
        print(all_docs['documents'][i][:200] + "...")
else:
    print("❌ The database is empty!")