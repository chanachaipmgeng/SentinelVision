from fastapi import APIRouter, status

from ..controllers.system_controller import rebuild_face_index

router = APIRouter()

@router.post("/rebuild-index", 
             status_code=status.HTTP_200_OK, 
             tags=["System"],
             summary="Rebuild Face Recognition Index")
async def rebuild_index_route():
    """
    Triggers a full rebuild of the FAISS search index from all face encodings in the database.
    This should be called after adding or deleting a significant number of faces.
    """
    return await rebuild_face_index()
