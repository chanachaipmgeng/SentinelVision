import os
from fastapi import UploadFile
from pathlib import Path

UPLOAD_DIR = Path("uploads")

async def save_uploaded_file(upload_file: UploadFile) -> str:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / upload_file.filename
    with open(file_path, "wb") as buffer:
        buffer.write(await upload_file.read())
    return str(file_path)
