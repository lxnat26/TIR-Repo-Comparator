import hashlib
import json
from pathlib import Path
from datetime import datetime
import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
from langchain_ollama import ChatOllama # Added for LLM extraction

ROOT_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT_DIR / "processed_reports"
DB_PATH = str(ROOT_DIR / "pharma_db")
COLLECTION_NAME = "pharma_reports"

# 1. Setup the Embedding Model (The Librarian)
embedding_fn = OllamaEmbeddingFunction(
    model_name="nomic-embed-text",
    url="http://localhost:11434/api/embeddings",
)

# 2. Setup the LLM (The Data Extractor)
llm = ChatOllama(model="llama3.2", format="json", temperature=0)

def extract_metadata_with_ai(text_content):
    """Uses LLM to find company, drug, and date inside the text."""
    snippet = text_content[:2000] # Give AI the first page/2000 chars
    
    prompt = f"""
    Analyze the following clinical report text and extract metadata into a JSON object.
    
    RULES:
    1. report_date must be in YYYY-MM-DD format.
    2. Use "Unknown" for any missing fields.
    3. Output ONLY valid JSON.

    Required keys: "company_name", "drug_name", "report_date"
    
    Text:
    {snippet}
    """
    try:
        response = llm.invoke(prompt)
        data = json.loads(response.content)
        
        # Validation: Force values to be strings to prevent ChromaDB errors
        return {
            "company_name": str(data.get("company_name", "Unknown")),
            "drug_name": str(data.get("drug_name", "Unknown")),
            "report_date": str(data.get("report_date", "Unknown"))
        }
    except Exception as e:
        print(f"⚠️ Metadata extraction failed: {e}")
        return {"company_name": "Unknown", "drug_name": "Unknown", "report_date": "Unknown"}

def index_processed_data():
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
    )

    md_files = list(PROCESSED_DIR.glob("*.md"))
    
    for md_path in md_files:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Step 1: Duplicate Prevention
        doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        if collection.get(where={"doc_id": doc_id})["ids"]:
            print(f"⏭️ Already indexed: {md_path.name}")
            continue

        # Step 2: Dynamic LLM Metadata Extraction
        print(f"🧠 AI is reading {md_path.name} to extract metadata...")
        ai_meta = extract_metadata_with_ai(content)

        # Step 3: Chunking
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = text_splitter.split_text(content)
        
        timestamp = datetime.utcnow().isoformat()

        # Step 4: Map Metadata to every chunk
        ids, documents, metadatas = [], [], []
        for i, chunk in enumerate(chunks):
            ids.append(f"{doc_id}_chunk_{i}")
            documents.append(chunk)
            
            # This satisfies your exact requirement for metadata fields
            metadatas.append({
                "doc_id": doc_id,
                "source": md_path.name,
                "chunk_index": i,
                "uploaded_at": timestamp,
                "file_type": "markdown",
                "company_name": ai_meta.get("company_name", "Unknown"),
                "drug_name": ai_meta.get("drug_name", "Unknown"),
                "report_date": ai_meta.get("report_date", "Unknown"),
            })

        # Step 5: Vectorize and Store
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"✅ {md_path.name}: Successfully indexed {len(chunks)} chunks.")

if __name__ == "__main__":
    index_processed_data()