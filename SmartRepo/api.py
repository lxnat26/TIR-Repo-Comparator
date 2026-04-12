from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
import uuid
from datetime import datetime

from SmartRepo.store_reports import ingest_pdf, collection

app = FastAPI()

# allows front end port and backend port connect without being blocked by browser securities
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DOCS_PATH = Path("SmartRepo/docs")
DOCS_PATH.mkdir(parents=True, exist_ok=True)


# changed path to match frontend api.ts is calling
@app.post("/api/documents/upload")
async def upload_file(file: UploadFile = File(...)):

    save_path = DOCS_PATH / file.filename

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    ingest_pdf(save_path)

    # format with data matches for frontend
    return {
        "id": str(uuid.uuid4()),
        "filename": file.filename,
        "file_type": file.filename.rsplit(".", 1)[-1].lower(),
        "uploaded_at": datetime.utcnow().isoformat(),
        "status": "ready",
    }

# returns list of all unique documents stored in chromadb
@app.get("/api/documents")
async def list_documents():
    results = collection.get(include=["metadatas"])

    # group chunks by doc_id so we return one entry per document not chunk
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