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

# 2. Inspect the first chunk's metadata
if len(all_docs['ids']) > 0:
    print("\n🔍 --- Sample Metadata Record ---")
    print(all_docs['metadatas'][0]) 
    
    print("\n📄 --- Sample Text Snippet ---")
    print(all_docs['documents'][0][:200] + "...")
else:
    print("❌ The database is empty!")