from pathlib import Path
import sys
import shutil  # Add this for folder deletion

# Setup paths
ROOT_DIR = Path(__file__).resolve().parents[2]

import parser
import vector_store

def run_ingestion_pipeline(pdf_filename):
    print("\n--- Starting Full Data Pipeline ---")
    
    pdf_path = ROOT_DIR / pdf_filename
    db_path = ROOT_DIR / "pharma_db" # The location of the vector store

    if not pdf_path.exists():
        print(f"Error: {pdf_filename} not found")
        return False

    # --- NEW: CLEAR OLD DATA ---
    if db_path.exists():
        print(f"🧹 Clearing old database at {db_path}...")
        shutil.rmtree(db_path) 

    # Stage 1: Parser
    print("\n[1/2] Shredding PDF...")
    parser.run_smart_parser(pdf_path)

    # Stage 2: Vector Store
    print("\n[2/2] Indexing data into Vector Store...")
    vector_store.index_processed_data()

    print("\n--- Data Pipeline Complete ---")
    return True

if __name__ == "__main__":
    run_ingestion_pipeline("2024_lilly_lebrikizumab_phase2_update.pdf")