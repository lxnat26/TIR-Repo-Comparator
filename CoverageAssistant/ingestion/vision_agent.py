import os
import base64
from pathlib import Path
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

llm = ChatOllama(model="llama3.2-vision")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def run_vision_analysis():
    """ENTRY POINT FOR ORCHESTRATOR"""
    # Dynamic pathing relative to this file
    ROOT_DIR = Path(__file__).resolve().parents[2]
    image_folder = ROOT_DIR / "processed_reports" / "images"
    output_path = ROOT_DIR / "processed_reports" / "image_descriptions.txt"

    if not image_folder.exists():
        print(f"❌ No images found at {image_folder}")
        return

    descriptions = []
    image_files = [f for f in os.listdir(image_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]

    print(f"--- 👁️ Analyzing {len(image_files)} images ---")

    for image_file in image_files:
        image_path = image_folder / image_file
        base64_image = encode_image(image_path)

        message = HumanMessage(
            content=[
                {"type": "text", "text": "Describe this pharmaceutical chart. Use exact integers for axes."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
            ],
        )

        print(f"🔍 Analyzing {image_file}...")
        response = llm.invoke([message])
        descriptions.append(f"IMAGE: {image_file}\nDESCRIPTION: {response.content}\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(descriptions))
    
    print(f"--- ✅ Descriptions saved to {output_path} ---")

if __name__ == "__main__":
    run_vision_analysis()