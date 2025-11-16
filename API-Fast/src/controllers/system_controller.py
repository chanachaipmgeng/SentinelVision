from fastapi import APIRouter, Depends, HTTPException, status
from ..utils.face_index import build_and_save_index

async def rebuild_face_index():
    """
    Triggers the process to rebuild the FAISS index from the database.
    """
    try:
        await build_and_save_index()
        return {"message": "Face recognition index rebuilt successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rebuild index: {str(e)}"
        )
