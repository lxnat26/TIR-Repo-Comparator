import os
from pathlib import Path
from unstructured.partition.pdf import partition_pdf

# 1. Setup the Folders
# We need a place to put the "shredded" text
# This finds the 'CoverageAssistant' root folder
ROOT_DIR = Path(__file__).resolve().parents[2]
INPUT_DIR = ROOT_DIR / "SmartRepo"/ "docs"
OUTPUT_DIR = ROOT_DIR / "processed_reports"

# Ensure directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def run_smart_parser(pdf_path):
    print(f"--- Starting Smart Parse on: {pdf_path} ---")

    # 2. The "Shredder" (partition_pdf)
    # This is the heavy lifter. It 'looks' at the PDF layout.
    elements = partition_pdf(
        filename=pdf_path,
        strategy="fast",              # 'fast' is best if the PDF is text-based (not a scan)
        extract_images_in_pdf=False,  # DO NOT crop images
        infer_table_structure=True,   # Still keeps tables as text
        chunking_strategy="by_title", # Keeps the context grouped by headers
        max_characters=4000,
        new_after_n_chars=3800,
    )

    # 3. Create the "Smart" Markdown File
    # We turn the 'elements' into a clean .md file for the AI to read later
    md_output_path = OUTPUT_DIR / f"{pdf_path.stem}.md"
    
    with md_output_path.open("w", encoding="utf-8") as f:
        for element in elements:
            # We add double newlines to keep the AI from getting confused
            f.write(str(element) + "\n\n")

    print(f" Saved → {md_output_path.name}")

# --- MAIN EXECUTION ---
# This looks for any PDF in your current folder and runs the code
if __name__ == "__main__":
    pdf_files = list(INPUT_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No PDFs found.")
    else:
        for pdf in pdf_files:
            run_smart_parser(pdf)