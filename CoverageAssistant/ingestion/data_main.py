from pathlib import Path
import shutil

# Setup paths
ROOT_DIR = Path(__file__).resolve().parents[2]
INPUT_DIR = ROOT_DIR / "SmartRepo" / "docs"
DB_PATH = ROOT_DIR / "pharma_db"

import parser
import vector_store


def run_ingestion_pipeline():
    print("\n--- Starting Full Data Pipeline ---")

    print(f"Looking for PDFs in: {INPUT_DIR.resolve()}")

    if not INPUT_DIR.exists():
        print("❌ Input directory not found.")
        return False

    pdf_files = list(INPUT_DIR.rglob("*.pdf"))

    if not pdf_files:
        print("❌ No PDFs found.")
        return False

    print(f"✅ Found {len(pdf_files)} PDFs")

    # --- CLEAR DB ONCE ---
    if DB_PATH.exists():
        print(f"🧹 Clearing old database at {DB_PATH}...")
        shutil.rmtree(DB_PATH)

    # --- STAGE 1: PARSING ---
    print("\n[1/2] Shredding PDFs...")
    parsed_count = 0

    for pdf in pdf_files:
        try:
            parser.run_smart_parser(pdf)
            parsed_count += 1
        except Exception as e:
            print(f"❌ Failed parsing {pdf.name}: {e}")

    print(f"\nParsed {parsed_count}/{len(pdf_files)} PDFs")

    # --- STAGE 2: VECTOR STORE ---
    print("\n[2/2] Indexing all processed data...")
    vector_store.index_processed_data()

    print("\n--- Data Pipeline Complete ---")
    return True


if __name__ == "__main__":
    run_ingestion_pipeline()