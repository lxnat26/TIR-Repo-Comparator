from fastapi import FastAPI, UploadFile, File
from pathlib import Path
import shutil

from SmartRepo.store_reports import ingest_pdf

app = FastAPI()

DOCS_PATH = Path("SmartRepo/docs")
DOCS_PATH.mkdir(parents=True, exist_ok=True)


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):

    save_path = DOCS_PATH / file.filename

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    ingest_pdf(save_path)

    return {
        "status": "success",
        "filename": file.filename
    }