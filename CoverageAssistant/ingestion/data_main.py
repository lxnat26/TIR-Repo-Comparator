from pathlib import Path
import shutil
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))  # adds ingestion/ to path

INPUT_DIR = ROOT_DIR / "SmartRepo" / "docs"
DB_PATH = ROOT_DIR / "pharma_db"
PROCESSED_DIR = ROOT_DIR / "processed_reports"

import parser as pdf_parser
import vector_store_aligned


def ingest_pdf(pdf_path: Path) -> None:
    """Parse one PDF → markdown → index into pharma_db.

    Used by both the per-upload API path and the batch run_ingestion_pipeline().
    """
    pdf_path = Path(pdf_path)
    print(f"📄 Parsing {pdf_path.name}")
    pdf_parser.run_smart_parser(pdf_path)

    md_path = PROCESSED_DIR / f"{pdf_path.stem}.md"
    if not md_path.exists():
        print(f"❌ Expected markdown not found after parsing: {md_path}")
        return

    vector_store_aligned.index_single_markdown(md_path)


def run_ingestion_pipeline():
    """Batch entry point — parses every PDF in SmartRepo/docs and indexes each."""
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

    if DB_PATH.exists():
        print(f"🧹 Clearing old database at {DB_PATH}...")
        shutil.rmtree(DB_PATH)

    parsed_count = 0
    for pdf in pdf_files:
        try:
            ingest_pdf(pdf)
            parsed_count += 1
        except Exception as e:
            print(f"❌ Failed ingesting {pdf.name}: {e}")

    print(f"\nIngested {parsed_count}/{len(pdf_files)} PDFs")
    print("\n--- Data Pipeline Complete ---")
    return True


if __name__ == "__main__":
    run_ingestion_pipeline()
