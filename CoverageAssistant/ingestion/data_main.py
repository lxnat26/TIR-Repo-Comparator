from pathlib import Path
import sys
import json
import hashlib

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = ROOT_DIR / "SmartRepo" / "docs"
PROCESSED_DIR = ROOT_DIR / "processed_reports"
MANIFEST_PATH = ROOT_DIR / "ingestion_manifest.json"

import parser as pdf_parser
import vector_store_aligned


def file_hash(path: Path) -> str:
    """Create hash of original PDF/DOCX so unchanged files can be skipped."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with MANIFEST_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest: dict) -> None:
    with MANIFEST_PATH.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def ingest_document(doc_path: Path) -> bool:
    """Parse one PDF/DOCX only if needed, then index markdown."""
    doc_path = Path(doc_path)

    print(f"📄 Parsing {doc_path.name}")
    pdf_parser.run_smart_parser(doc_path)

    md_path = PROCESSED_DIR / f"{doc_path.stem}.md"
    if not md_path.exists():
        print(f"❌ Expected markdown not found after parsing: {md_path}")
        return False

    chunks_added = vector_store_aligned.index_single_markdown(md_path)
    return chunks_added >= 0


def run_ingestion_pipeline():
    print("\n--- Starting Incremental Data Pipeline ---")
    print(f"Looking for PDF/DOCX files in: {INPUT_DIR.resolve()}")

    if not INPUT_DIR.exists():
        print("❌ Input directory not found.")
        return False

    doc_files = list(INPUT_DIR.rglob("*.pdf")) + list(INPUT_DIR.rglob("*.docx"))
    if not doc_files:
        print("❌ No PDF or DOCX files found.")
        return False

    manifest = load_manifest()

    processed_count = 0
    skipped_count = 0

    for doc in doc_files:
        try:
            current_hash = file_hash(doc)
            manifest_key = str(doc.relative_to(INPUT_DIR))

            if manifest.get(manifest_key) == current_hash:
                print(f"⏭️ Skipping unchanged file: {doc.name}")
                skipped_count += 1
                continue

            success = ingest_document(doc)

            if success:
                manifest[manifest_key] = current_hash
                save_manifest(manifest)
                processed_count += 1

        except Exception as e:
            print(f"❌ Failed ingesting {doc.name}: {e}")

    print(f"\n✅ Processed new/changed files: {processed_count}")
    print(f"⏭️ Skipped unchanged files: {skipped_count}")
    print("--- Data Pipeline Complete ---")
    return True


if __name__ == "__main__":
    run_ingestion_pipeline()