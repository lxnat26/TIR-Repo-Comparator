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
    Extract clinical report metadata from the text below into a JSON object.
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
    md_path = ROOT_DIR / "processed_reports" / "final_report2.md" # Updated to final_report2
    db_path = str(ROOT_DIR / "pharma_db")

    if not md_path.exists():
        print(f"Error: {md_path} not found.")
        return

    # Read the parsed text
    with open(md_path, "r", encoding="utf-8") as f:
        report_content = f.read()

    # 1. Split the text into chunks first
    headers_to_split_on = [("#", "Header 1"), ("##", "Header 2")]
    header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    chunks = header_splitter.split_text(report_content)

    # 2. NOW loop through the chunks and inject the AI metadata
    # Make sure this happens AFTER the split_text call
    metadata = extract_metadata_with_ai(report_content)
    metadata["source"] = md_path.name

    for chunk in chunks:
        # This ensures every individual piece of text carries the labels
        chunk.metadata.update(metadata)
        # chunk.metadata = metadata.copy()
        

    print(f"--- Indexing {len(chunks)} sections ---")

    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=db_path,
        collection_name="pharma_reports"
    )
    print(f"--- Vector Store Created in: {db_path} ---")

if __name__ == "__main__":
    index_processed_data()