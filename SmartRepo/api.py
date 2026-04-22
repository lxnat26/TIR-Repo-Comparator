from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
import uuid
import sys
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from CoverageAssistant.ingestion.data_main import ingest_pdf
from CoverageAssistant.ingestion.vector_store_aligned import get_collection
from CoverageAssistant.ingestion import parser as pdf_parser
from CoverageAssistant.backend.coverage_crew.main import run_on_text

PROCESSED_DIR = REPO_ROOT / "processed_reports"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DOCS_PATH = Path("SmartRepo/docs")
DOCS_PATH.mkdir(parents=True, exist_ok=True)


@app.post("/api/documents/upload")
async def upload_file(file: UploadFile = File(...)):
    save_path = DOCS_PATH / file.filename
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    ingest_pdf(save_path)
    return {
        "id": str(uuid.uuid4()),
        "filename": file.filename,
        "file_type": file.filename.rsplit(".", 1)[-1].lower(),
        "uploaded_at": datetime.utcnow().isoformat(),
        "status": "ready",
    }


@app.get("/api/documents")
async def list_documents():
    results = get_collection().get(include=["metadatas"])
    seen = {}
    for metadata in results["metadatas"]:
        doc_id = metadata["doc_id"]
        if doc_id not in seen:
            seen[doc_id] = {
                "id": doc_id,
                "filename": Path(metadata["source"]).name,
                "file_type": metadata["file_type"],
                "uploaded_at": metadata["uploaded_at"],
                "status": "ready",
            }
    return list(seen.values())


@app.post("/api/analyze/document")
async def analyze_document(
    file: UploadFile = File(...),
    competitor: Optional[str] = Form(None),
    drug: Optional[str] = Form(None),
):

    save_path = DOCS_PATH / file.filename
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    pdf_parser.run_smart_parser(save_path)

    md_path = PROCESSED_DIR / f"{save_path.stem}.md"
    with md_path.open("r", encoding="utf-8") as f:
        document_text = f.read()

    # 2. Run the crew on extracted text
    try:
        result = run_on_text(
            report_text=document_text,
            drug_name=drug,
            company_name=competitor,
        )
        claims = result.get("claims", [])
    except Exception as e:
        print(f"❌ Crew error: {e}")
        claims = []

    return {
        "claim_count": len(claims),
        "claims": claims,
        "analyzed_at": datetime.utcnow().isoformat(),
        "document_text": document_text,
    }


class AnalyzeTextRequest(BaseModel):
    text: str
    competitor: Optional[str] = None
    drug: Optional[str] = None


@app.post("/api/analyze")
async def analyze_text(req: AnalyzeTextRequest):
    try:
        result = run_on_text(
            report_text=req.text,
            drug_name=req.drug,
            company_name=req.competitor,
        )
        claims = result.get("claims", [])
    except Exception as e:
        print(f"❌ Crew error: {e}")
        claims = []

    return {
        "claim_count": len(claims),
        "claims": claims,
        "analyzed_at": datetime.utcnow().isoformat(),
        "document_text": req.text,
    }