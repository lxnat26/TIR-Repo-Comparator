from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
import chromadb
from pathlib import Path

# Setup paths
ROOT_DIR = Path(__file__).resolve().parents[2]
db_path = str(ROOT_DIR / "pharma_db")
COLLECTION_NAME = "pharma_reports" # Defined globally for consistency
embeddings = OllamaEmbeddings(model="nomic-embed-text")

def inspect_database_samples():
    """Prints a general overview of what is in the DB."""
    # Connect via LangChain wrapper
    vector_db = Chroma(
        persist_directory=db_path,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME
    )

    all_docs = vector_db.get()
    print(f"📊 Total chunks in database: {len(all_docs['ids'])}")

    if len(all_docs['ids']) > 0:
        print("\n🔍 --- Sample Records (First 5) ---")
        sample_size = min(5, len(all_docs['ids']))        
        
        for i in range(sample_size):
            print(f"\n--- Chunk {i+1} ---")
            print(f"Source: {all_docs['metadatas'][i].get('source')}")
            print(f"Metadata: {all_docs['metadatas'][i]}")
            print(f"Text Snippet: {all_docs['documents'][i][:150]}...")
    else:
        print("❌ The database is empty!")

def check_file_metadata(filename):
    """Retrieves metadata for a specific file using the direct Chroma client."""
    client = chromadb.PersistentClient(path=db_path)
    
    try:
        # Access the collection directly
        collection = client.get_collection(name=COLLECTION_NAME)
        
        results = collection.get(
            where={"source": filename},
            include=["metadatas", "documents"]
        )

        if not results["ids"]:
            print(f"\n❌ No records found for file: {filename}")
            return

        print(f"\n🔍 Found {len(results['ids'])} chunks for '{filename}'")
        print("-" * 50)
        
        # Check metadata from the first chunk
        sample_meta = results["metadatas"][0]
        print(f"📄 SOURCE:       {sample_meta.get('source')}")
        print(f"🏢 COMPANY:      {sample_meta.get('company_name')}")
        print(f"💊 DRUG:         {sample_meta.get('drug_name')}")
        print(f"📅 REPORT DATE:  {sample_meta.get('report_date')}")
        print(f"🕒 UPLOADED AT:  {sample_meta.get('uploaded_at')}")
        print("-" * 50)
        print(f"📝 TEXT PREVIEW: {results['documents'][0][:150]}...")

    except Exception as e:
        print(f"❌ Error accessing collection: {e}")

if __name__ == "__main__":
    # 1. Show database stats
    # inspect_database_samples()
    
    # 2. Check specific file
    # Use the .md version as stored in your processing pipeline
    target_file = "2.20.2026 - FDA Approval of Venclexta+Calquence AMPLIFY in 1L CLL Alert_[comments addressed].md"
    check_file_metadata(target_file)