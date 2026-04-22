import os
from pathlib import Path
from unstructured.partition.pdf import partition_pdf
from text_metadata_utils import normalize_text

ROOT_DIR = Path(__file__).resolve().parents[2]
INPUT_DIR = ROOT_DIR / "SmartRepo" / "docs"
OUTPUT_DIR = ROOT_DIR / "processed_reports"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def clean_markdown(content: str) -> str:
    """Remove chart junk but preserve useful metadata/header lines."""
    content = normalize_text(content)

    keep_prefixes = (
        "Company:",
        "Drug:",
        "Date:",
        "Publication Date:",
        "Indication:",
        "Source:",
    )

    clean_lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Always preserve useful metadata lines
        if stripped.startswith(keep_prefixes):
            clean_lines.append(stripped)
            continue

        words = [w for w in stripped.split() if w.isalpha() and len(w) > 2]

        # Keep longer meaningful lines
        if len(stripped) >= 40 and len(words) >= 5:
            clean_lines.append(stripped)

    return "\n".join(clean_lines)

def run_smart_parser(pdf_path):
    print(f"--- Starting Smart Parse on: {pdf_path} ---")

    elements = partition_pdf(
        filename=pdf_path,
        strategy="hi_res",
        include_header=True,
        extract_images_in_pdf=False,
        infer_table_structure=True,
        chunking_strategy="by_title",
        max_characters=1500,
    )

    md_output_path = OUTPUT_DIR / f"{pdf_path.stem}.md"

    # Write raw output
    with md_output_path.open("w", encoding="utf-8") as f:
        for element in elements:
            f.write(str(element) + "\n\n")

    # Clean up chart/image artifacts
    with md_output_path.open("r", encoding="utf-8") as f:
        content = f.read()

    cleaned = clean_markdown(content)

    with md_output_path.open("w", encoding="utf-8") as f:
        f.write(cleaned)

    print(f" Saved → {md_output_path.name}")


if __name__ == "__main__":
    pdf_files = list(INPUT_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No PDFs found.")
    else:
        for pdf in pdf_files:
            run_smart_parser(pdf)