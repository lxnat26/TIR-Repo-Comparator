# TIR-Repo-Comparator: Coverage Assistant

An AI-powered system for extracting, comparing, and classifying clinical and regulatory claims from pharmaceutical reports using **CrewAI** and local **Ollama LLMs**.

## Overview

The Coverage Assistant uses a multi-agent architecture to:
1. **Extract** clinical claims (efficacy, safety, milestones) from reports
2. **Compare** newly extracted claims against historical data
3. **Classify** claims based on novelty, contradictions, and significance

All processing is **100% local** — no external APIs or cloud dependency.

## 📋 Prerequisites

### 1. Ollama Models (Required)

You **must** have these models downloaded locally:

```bash
ollama pull llama3.1           # For claim extraction & classification
ollama pull nomic-embed-text   # For vector embeddings & search
```

Start Ollama server:
```bash
ollama serve
```

### 2. Python Environment

Create and activate virtual environment:

```bash
# Create venv
python3 -m venv venv

# Activate
# Mac/Linux:
source venv/bin/activate

# Windows:
.\venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. System Dependencies (Non-Python)

The `unstructured` library requires:

- **Mac:** `brew install tesseract poppler`
- **Windows:** Download Tesseract & Poppler, add to System PATH
- **Linux:** `apt-get install tesseract-ocr poppler-utils`

### 5. Environment Configuration

Create a `.env` file in the project root (optional):

```env
OPENAI_API_KEY=your_key_here  # Only if using OpenAI instead of Ollama
```

## 📁 Project Structure

```
TIR-Repo-Comparator/
├── CoverageAssistant/
│   ├── backend/
│   │   └── coverage_crew/          # CrewAI agents & tasks
│   │       ├── config/
│   │       │   ├── agents.yaml     # Agent configurations
│   │       │   └── tasks.yaml      # Task definitions
│   │       ├── tools/
│   │       │   └── query_chromadb.py
│   │       ├── utils/
│   │       │   └── helpers.py
│   │       ├── crew.py             # Crew definition
│   │       └── main.py             # Entry point
│   ├── ingestion/
│   │   ├── parser.py               # Document parsing
│   │   └── vector_store_aligned.py # Vector store management
│   └── CoverageAssistantSite/      # Web interface (optional)
├── SmartRepo/
│   └── docsInput/                  # Input documents
├── processed_reports/              # Extracted markdown & images
├── pharma_db/                      # ChromaDB vector store (auto-created)
├── requirements.txt                # Python dependencies
└── README.md
```

## 🚀 Quick Start

### 1. Prepare Documents

Place PDF or DOCX files in:
```
SmartRepo/docsInput/
```

### 2. Run the Coverage Assistant

```bash
cd CoverageAssistant/backend/coverage_crew
python main.py
```

The system will:
- Parse the input document
- Extract claims using CrewAI agent
- Search for historical matches in the database
- Compare against previous records
- Classify as novel/updated/contradictory

### 3. View Results

Extracted claims are saved as JSON in the crew's output.

## 🔧 Configuration

### Agent LLM Selection

Edit `CoverageAssistant/backend/coverage_crew/config/agents.yaml`:

**For local Ollama (default):**
```yaml
claim_extractor:
  llm: ollama/llama3.1
```

**For OpenAI:**
```yaml
claim_extractor:
  llm: gpt-4
```

### Claim Classifications

The system extracts three types of claims:

| Type | Definition | Examples |
|------|-----------|----------|
| **milestone** | Regulatory/trial events | FDA approval, trial phase completion, data release |
| **efficacy** | Drug effectiveness data | Response rates, survival improvements, clinical outcomes |
| **safety** | Adverse events & tolerability | Side effects, discontinuation rates, tolerability data |

## 📊 Data Pipeline

```
Input Document
    ↓
Smart Parse (extract text/images)
    ↓
Metadata Extraction (drug, company, date)
    ↓
Claim Extraction (CrewAI Agent)
    ↓
Vector Embedding (nomic-embed-text)
    ↓
ChromaDB Search (find historical matches)
    ↓
Claim Comparison (CrewAI Agent)
    ↓
Claim Classification (CrewAI Agent)
    ↓
JSON Output
```

## 🔒 Data Privacy & Security

- ✅ **100% Local Processing** — No cloud APIs or external services
- ✅ **No Data Transmission** — All data stays on your machine
- ✅ **Local LLMs** — Using Ollama with open-source models
- ✅ **Local Vector DB** — ChromaDB persisted locally in `/pharma_db`

## 📝 Example Output

```json
{
  "claims": [
    {
      "claim_type": "milestone",
      "specific_type": "drug approval",
      "claim": "Jaypirca received FDA traditional approval Dec 3, 2025 for relapsed/refractory CLL/SLL"
    },
    {
      "claim_type": "efficacy",
      "specific_type": "",
      "claim": "Lilly's Jaypirca met primary endpoint in Phase 3 BRUIN CLL-322 trial, significantly extending progression-free survival"
    }
  ]
}
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: crewai` | Run `pip install -r requirements.txt` |
| ChromaDB corruption error | Delete `pharma_db/` folder, it will rebuild |
| Ollama connection refused | Ensure `ollama serve` is running in separate terminal |
| OCR/Tesseract errors | Install system dependencies: `brew install tesseract poppler` |
| Document parsing errors | Ensure PDF/DOCX is valid; check `processed_reports/` for output |

## 🤝 Contributing

To extend the system:

1. **Add new agents** — Edit `CoverageAssistant/backend/coverage_crew/config/agents.yaml`
2. **Modify tasks** — Edit `CoverageAssistant/backend/coverage_crew/config/tasks.yaml`
3. **Add tools** — Create new tools in `CoverageAssistant/backend/coverage_crew/tools/`

## 📚 References

- [CrewAI Documentation](https://crewai.io)
- [Ollama Models](https://ollama.ai)
- [LangChain Documentation](https://langchain.com)
- [ChromaDB Documentation](https://docs.trychroma.com)

## 🔒 Data Privacy & Security

- All processing is **locally executed**
- No external API calls (OpenAI/Claude)
- Vector database stored in `/pharma_db`