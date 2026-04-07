import os
import base64
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

# 1. Setup the Vision Model
# This is the "Brain" that can see images
llm = ChatOllama(model="llama3.2-vision")

def encode_image(image_path):
    """Helper: Converts an image file into a Base64 string for the AI."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def describe_images(image_folder):
    descriptions = []
    # Grab all the images your parser.py cropped
    image_files = [f for f in os.listdir(image_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]

    if not image_files:
        print("❌ No images found. Did you run parser.py?")
        return

    print(f"--- 👁️ LangChain is analyzing {len(image_files)} images ---")

    for image_file in image_files:
        image_path = os.path.join(image_folder, image_file)
        base64_image = encode_image(image_path)

        # 2. Create the Multimodal Message
        # We send both the text prompt AND the image data
        message = HumanMessage(
            content=[
                {
                    "type": "text", 
                    "text": (
                        "Describe this pharmaceutical chart or table in 2-3 sentences. Focus on the data and trends. "
                        "CRITICAL: If a data point or bar is exactly on a whole number line (like 4), "
                        "do not provide a range or estimate (e.g., do not say '4 to 4.5'). "
                        "Use the exact integer shown on the axis."
                    )
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ],
        )

        # 3. Get the Response
        print(f"🔍 Analyzing {image_file}...")
        response = llm.invoke([message])
        
        descriptions.append(f"IMAGE: {image_file}\nDESCRIPTION: {response.content}\n")

    # 4. Save to a text file
    output_path = "processed_reports/image_descriptions.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(descriptions))
    
    print(f"--- ✅ Done! Descriptions saved to {output_path} ---")

if __name__ == "__main__":
    IMAGE_DIR = "processed_reports/images"
    if os.path.exists(IMAGE_DIR):
        describe_images(IMAGE_DIR)
    else:
        print(f"❌ Error: {IMAGE_DIR} not found.")