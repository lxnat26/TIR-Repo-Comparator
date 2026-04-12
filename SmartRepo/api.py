from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
import uuid
from datetime import datetime

from SmartRepo.store_reports import ingest_pdf

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