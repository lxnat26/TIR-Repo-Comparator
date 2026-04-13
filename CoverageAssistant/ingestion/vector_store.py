import os
from pathlib import Path
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import MarkdownHeaderTextSplitter

embeddings = OllamaEmbeddings(model="nomic-embed-text")

def index_processed_data():
    """ENTRY POINT FOR ORCHESTRATOR"""
    ROOT_DIR = Path(__file__).resolve().parents[2]
    md_path = ROOT_DIR / "processed_reports" / "final_report2.md" # Updated to final_report2
    desc_path = ROOT_DIR / "processed_reports" / "image_descriptions.txt"
    db_path = str(ROOT_DIR / "pharma_db")

    if not md_path.exists():
        print(f"❌ Error: {md_path} not found.")
        return

    with open(md_path, "r", encoding="utf-8") as f:
        report_content = f.read()

    if desc_path.exists():
        print("🔗 Merging image descriptions...")
        with open(desc_path, "r", encoding="utf-8") as f:
            report_content += "\n\n## AI Visual Analysis\n" + f.read()

    headers_to_split_on = [("#", "Header 1"), ("##", "Header 2")]
    header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    chunks = header_splitter.split_text(report_content)

    print(f"--- 📚 Indexing {len(chunks)} sections ---")

    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=db_path,
        collection_name="pharma_reports"
    )
    print(f"--- ✅ Vector Store Created in: {db_path} ---")

if __name__ == "__main__":
    index_processed_data()