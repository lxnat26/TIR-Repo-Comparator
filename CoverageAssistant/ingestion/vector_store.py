import os
import re
import json
from pathlib import Path
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_text_splitters import MarkdownHeaderTextSplitter

embeddings = OllamaEmbeddings(model="nomic-embed-text")
llm = ChatOllama(model="llama3.2", format="json", temperature=0) # Use a small, fast model

def extract_metadata_with_ai(file_content):
    # Clinical reports usually put the metadata on the first page
    snippet = file_content[:1500]
    
    prompt = f"""
    You are a data extraction bot. Extract clinical report metadata into a JSON object.
    
    STRICT RULES:
    1. Output ONLY valid JSON.
    2. The "report_date" MUST be in YYYY-MM-DD format (e.g., 2024-09-21). 
    3. If a date is "September 21, 2024", convert it to "2024-09-21".
    4. If any field is missing, use "Unknown".

    Required keys: "company_name", "drug_name", "report_date".
    
    Text:
    {snippet}
    """
    
    try:
        response = llm.invoke(prompt)
        content = response.content.strip()

        # Handle Markdown code blocks if the AI included them
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        return json.loads(content.strip())

    except Exception as e:
        # If it fails, print the actual AI response so you can see what went wrong
        print(f"⚠️ AI Response was: {response.content if 'response' in locals() else 'No response'}")
        print(f"⚠️ Error parsing JSON: {e}")
        return {"company_name": "Unknown", "drug_name": "Unknown", "report_date": "Unknown"}


def index_processed_data():
    """ENTRY POINT FOR ORCHESTRATOR"""
    ROOT_DIR = Path(__file__).resolve().parents[2]
    md_dir = ROOT_DIR / "processed_reports"
    db_path = str(ROOT_DIR / "pharma_db")

    md_files = list(md_dir.glob("*.md"))

    print(f"Found {len(md_files)} markdown files")

    if not md_files:
        print(f"Error: {md_path} not found.")
        return
    all_chunks = []

    for md_path in md_files:
        print(f"--- Processing: {md_path.name} ---")

        with open(md_path, "r", encoding="utf-8") as f:
            report_content = f.read()

        # Split into sections
        headers_to_split_on = [("#", "Header 1"), ("##", "Header 2")]
        splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        chunks = splitter.split_text(report_content)

        # Extract metadata per document
        metadata = extract_metadata_with_ai(report_content)
        metadata["source"] = md_path.name

        for chunk in chunks:
            chunk.metadata.update(metadata)

        all_chunks.extend(chunks)

    print(f"--- Total chunks: {len(all_chunks)} ---")

    vector_db = Chroma.from_documents(
        documents=all_chunks,
        embedding=embeddings,
        persist_directory=db_path,
        collection_name="pharma_reports"
    )

    print(f"--- Vector DB built at: {db_path} ---")

if __name__ == "__main__":
    index_processed_data()