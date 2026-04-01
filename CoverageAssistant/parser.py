import os
from unstructured.partition.pdf import partition_pdf
from unstructured.staging.base import convert_to_islands

# 1. Setup folders for our results
OUTPUT_DIR = "processed_reports"
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")
os.makedirs(IMAGE_DIR, exist_ok=True)

def parse_document_to_markdown(file_path):
    print(f"--- Starting Parse: {file_path} ---")

    # 2. The "Hi-Res" strategy tells the AI to "look" for images and tables
    elements = partition_pdf(
        filename=file_path,
        strategy="hi_res",                   # Uses Computer Vision to find layout
        extract_image_block_types=["Image"], # Specifically look for images
        extract_image_block_output_dir=IMAGE_DIR, # Where to save the .png files
    )

    # 3. Convert the elements into a clean Markdown string
    markdown_content = ""
    for el in elements:
        # Check the type of element (Header, NarrativeText, etc.)
        if el.category == "Title":
            markdown_content += f"# {el.text}\n\n"
        elif el.category == "ListItem":
            markdown_content += f"* {el.text}\n"
        elif el.category == "Image":
            # If it's an image, we leave a placeholder for our CrewAI agent
            # We use the metadata to find the filename Unstructured assigned
            image_filename = el.metadata.image_path if hasattr(el.metadata, 'image_path') else "unknown_image.png"
            markdown_content += f"\n![Analysis Needed]({image_filename})\n"
            markdown_content += "> [PENDING AI INTERPRETATION]\n\n"
        else:
            markdown_content += f"{el.text}\n\n"

    # 4. Save the Markdown file
    report_name = os.path.basename(file_path).replace(".pdf", ".md")
    save_path = os.path.join(OUTPUT_DIR, report_name)
    
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"--- Finished! Created: {save_path} and saved images to {IMAGE_DIR} ---")
    return save_path

# To run it, just uncomment the line below with your filename:
# parse_document_to_markdown("your_report.pdf")