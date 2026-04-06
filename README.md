# Pharma Report AI Parser

This project uses AI to parse pharmaceutical reports, extracting both text and image data.

## Setup Instructions
### 1. Model Requirements (Ollama)
You MUST have these two models downloaded locally to run the code:
- `ollama pull llama3.2-vision` (For reading charts/images)
- `ollama pull nomic-embed-text` (For searching the documents)

### 2. Environment Update
If you already have a `venv`, activate it and run:
`pip install -r requirements.txt`
*Note: If you see a 'chromadb' conflict, run: 
`pip install "chromadb~=1.1.0"`*

### 3. Project Structure
- **/processed_reports**: Where the AI saves the "Smart Markdown" and cropped images.
- **/pharma_db**: The local database folder. **Do not delete this** unless you want to re-index the documents.

4. **Dependencies:** Ensure `Tesseract` and `Poppler` are installed on your system.