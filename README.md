# Pharma Report AI Parser

This project uses AI to parse pharmaceutical reports, extracting both text and image data.

## Setup Instructions
### 1. Model Requirements (Ollama)
You MUST have these two models downloaded locally to run the code:
- `ollama pull llama3.2-vision` (For reading charts/images)
- `ollama pull nomic-embed-text` (For searching the documents)

### 2. Environment Update
Virtual Environment
Create it once:
python3 -m venv venv

Activate it (Crucial!):
source venv/bin/activate

Install the "Contract":
pip install -r requirements.txt

If you already have a `venv`, activate it and run:
`pip install -r requirements.txt`
*Note: If you see a 'chromadb' conflict, run: 
`pip install "chromadb~=1.1.0"`*

### 3. Project Structure
- **/processed_reports**: Where the AI saves the "Smart Markdown" and cropped images.
- **/pharma_db**: The local database folder. **Do not delete this** unless you want to re-index the documents.

### 4. System Dependencies (Non-Python)
The `unstructured` library requires these to be installed on your system, not just in Python:
- **Mac:** `brew install tesseract poppler`
- **Windows:** Download the Tesseract and Poppler binaries and add them to your System PATH.

## 🔒 Data Privacy & Security
- All processing is performed **locally**. 
- No data is sent to external APIs (OpenAI/Claude). 
- PDF content is stored locally in the `/pharma_db` vector store.