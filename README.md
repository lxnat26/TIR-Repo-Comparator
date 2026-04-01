# Pharma Report AI Parser

This project uses AI to parse pharmaceutical reports, extracting both text and image data.

## Setup Instructions
1. **Ollama:** Download from [ollama.com](https://ollama.com) and run:
   `ollama pull llama3.2-vision`
2. **Environment:**
   - Windows: `python -m venv venv` & `.\venv\Scripts\activate`
   - Mac: `python3 -m venv venv` & `source venv/bin/activate`
3. **Install Tools:**
   `pip install -r requirements.txt`
4. **Dependencies:** Ensure `Tesseract` and `Poppler` are installed on your system.