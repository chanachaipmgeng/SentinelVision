import os
from uuid import uuid4
import base64
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
import aiofiles

router = APIRouter()

# Directory for storing uploaded images
UPLOAD_DIR = "./uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)  # Create folder if it doesn't exist

@router.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    # Validate file type
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(
            status_code=400, detail="Only JPEG and PNG image files are allowed"
        )

    # Generate a new filename
    file_extension = os.path.splitext(file.filename)[-1].lower()
    new_filename = f"{uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, new_filename)

    # Save the file to the directory
    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    return JSONResponse(
        status_code=200,
        content={
            "message": "File uploaded successfully",
            "filename": new_filename,
            "path": f"/uploaded_images/{new_filename}",
        },
    )

@router.post("/upload-image-base64/")
async def upload_image_base64(base64_image: str = Form(...)):
    # Decode the base64 string
    try:
        # Extract file type from base64 string
        if base64_image.startswith("data:image/jpeg;base64,"):
            base64_image = base64_image.replace("data:image/jpeg;base64,", "")
            file_extension = ".jpg"
        elif base64_image.startswith("data:image/png;base64,"):
            base64_image = base64_image.replace("data:image/png;base64,", "")
            file_extension = ".png"
        else:
            raise HTTPException(status_code=400, detail="Unsupported image format")

        image_data = base64.b64decode(base64_image)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 string")

    # Generate a unique filename
    new_filename = f"{uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, new_filename)

    # Save the decoded image data to a file
    async with aiofiles.open(file_path, "wb") as out_file:
        await out_file.write(image_data)

    return JSONResponse(
        status_code=200,
        content={
            "message": "File uploaded successfully",
            "filename": new_filename,
            "path": f"/uploaded_images/{new_filename}",
        },
    )

@router.get("/get-image/{filename}")
async def get_image(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path, media_type="image/jpeg", filename=filename)

@router.get("/get-image-base64/{filename}")
async def get_image_base64(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    try:
        with open(file_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
        mime_type = "image/jpeg" if filename.endswith(".jpg") or filename.endswith(".jpeg") else \
                    "image/png" if filename.endswith(".png") else \
                    "application/octet-stream"
        return JSONResponse(content={
            "filename": filename,
            "mime_type": mime_type,
            "data": f"data:{mime_type};base64,{encoded_image}"
        })
    except Exception:
        raise HTTPException(status_code=500, detail="Error reading image")
