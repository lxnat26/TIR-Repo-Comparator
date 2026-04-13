from pathlib import Path
import sys

# Setup paths to find sibling files (parser, vision_agent, vector_store)
ROOT_DIR = Path(__file__).resolve().parents[2]

# Import your modules
import parser
import vision_agent
import vector_store

def run_ingestion_pipeline(pdf_filename):
    """
    Orchestrates the full data pipeline.
    """
    print("\n--- 🏁 Starting Full Data Pipeline ---")
    
    pdf_path = ROOT_DIR / pdf_filename
    if not pdf_path.exists():
        print(f"❌ Error: {pdf_filename} not found in {ROOT_DIR}")
        return False

    # Stage 1: Parser (PDF -> Markdown)
    print("\n📦 [1/3] Shredding PDF...")
    parser.run_smart_parser(pdf_path)

    # Stage 2: Vision Agent (Analyze Images)
    print("\n👁️ [2/3] Analyzing Images with Vision Agent...")
    # This assumes vision_agent.py has a run() or similar entry point
    vision_agent.run_vision_analysis()

    # Stage 3: Vector Store (Indexing)
    print("\n🧠 [3/3] Indexing data into Vector Store...")
    # This assumes vector_store.py has an entry point to index the results
    vector_store.index_processed_data()

    print("\n--- ✅ Data Pipeline Complete ---")
    return True

if __name__ == "__main__":
    # Test run
    run_ingestion_pipeline("2024_lilly_lebrikizumab_phase2_update.pdf")