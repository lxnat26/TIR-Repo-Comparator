import chromadb
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_chroma import Chroma

# 1. Setup the "Brain" for turning text into numbers (Embeddings)
# We use the fast 'nomic-embed-text' model from Ollama
embeddings = OllamaEmbeddings(model="nomic-embed-text")

def vectorize_report(markdown_path):
    # 2. Read your Enriched Markdown
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 3. Smart Splitting: We split the file by Headers (#, ##) 
    # This keeps "Side Effects" text separate from "Efficacy" text.
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
    ]
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    chunks = splitter.split_text(content)

    # 4. Store in ChromaDB
    # This creates a local folder called 'pharma_db'
    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="./pharma_db",
        collection_name="clinical_reports"
    )
    
    print(f"--- Vectorized {len(chunks)} sections into ChromaDB! ---")
    return vector_db

# To test:
# vectorize_report("processed_reports/your_report.md")