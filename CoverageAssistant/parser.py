import os
from unstructured.partition.pdf import partition_pdf

# 1. Setup the Folders
# We need a place to put the "shredded" text and the "cropped" images
OUTPUT_DIR = "processed_reports"
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

def run_smart_parser(pdf_path):
    print(f"--- 🚀 Starting Smart Parse on: {pdf_path} ---")

    # 2. The "Shredder" (partition_pdf)
    # This is the heavy lifter. It 'looks' at the PDF layout.
    elements = partition_pdf(
        filename=pdf_path,
        strategy="hi_res",           # 'hi_res' is required to find images/tables
        extract_images_in_pdf=True,  # This tells the code to "crop" charts
        extract_image_block_output_dir=IMAGE_DIR, # Where to save those crops
        infer_table_structure=True,  # Tries to turn tables into text
        chunking_strategy="by_title",# Groups text by headers (e.g. 'Results')
        max_characters=4000,
        new_after_n_chars=3800,
    )

    # 3. Create the "Smart" Markdown File
    # We turn the 'elements' into a clean .md file for the AI to read later
    md_output_path = os.path.join(OUTPUT_DIR, "final_report.md")
    
    with open(md_output_path, "w", encoding="utf-8") as f:
        for element in elements:
            # We add double newlines to keep the AI from getting confused
            f.write(str(element) + "\n\n")

    print(f"--- ✅ Done! Check the '{OUTPUT_DIR}' folder for results. ---")

# --- MAIN EXECUTION ---
# This looks for any PDF in your current folder and runs the code
if __name__ == "__main__":
    # Change "report.pdf" to whatever your PDF is named!
    target_pdf = "2024_lilly_lebrikizumab_phase2_update.pdf" 
    
    if os.path.exists(target_pdf):
        run_smart_parser(target_pdf)
    else:
        print(f"❌ Error: Could not find '{target_pdf}' in your folder.")