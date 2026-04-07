import os
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import MarkdownHeaderTextSplitter

# 1. Setup the "Math Engine" (Embeddings)
# nomic-embed-text is the standard for high-accuracy local RAG
embeddings = OllamaEmbeddings(model="nomic-embed-text")

def build_vector_store():
    # Paths to your "shredded" PDF and "AI Eyes" descriptions
    md_path = "processed_reports/final_report.md"
    desc_path = "processed_reports/image_descriptions.txt"
    db_path = "./pharma_db"

    # --- STAGE 1: LOAD TEXT DATA ---
    if not os.path.exists(md_path):
        print(f"❌ Error: {md_path} not found. Did you run parser.py?")
        return

    with open(md_path, "r", encoding="utf-8") as f:
        report_content = f.read()

    # --- STAGE 2: THE IN-MEMORY MERGE ---
    # We append the chart descriptions so the AI 'knows' what the images show
    if os.path.exists(desc_path):
        print("🔗 Merging image descriptions into the report context...")
        with open(desc_path, "r", encoding="utf-8") as f:
            vision_context = f.read()
            # We wrap it in a header so the splitter keeps it as one section
            report_content += "\n\n## AI Visual Analysis and Chart Data\n" + vision_context
    else:
        print("⚠️ Warning: No image descriptions found. Search will be text-only.")

    # --- STAGE 3: SMART CHUNKING ---
    # We split by headers (# and ##) so clinical data stays organized by section
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
    ]
    
    header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    chunks = header_splitter.split_text(report_content)

    print(f"--- 📚 Indexing {len(chunks)} sections into ChromaDB ---")

    # --- STAGE 4: CREATE THE DATABASE ---
    # This saves the 'pharma_db' folder to your local GitHub repo directory
    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=db_path,
        collection_name="pharma_reports"
    )

    print(f"--- ✅ Vector Store Created Successfully in: {db_path} ---")

if __name__ == "__main__":
    build_vector_store()