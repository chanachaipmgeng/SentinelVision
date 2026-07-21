from fastapi import APIRouter, status

from ..controllers.system_controller import rebuild_face_index

router = APIRouter()


@router.post(
    "/rebuild-index",
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Face index status (pgvector — no rebuild required)",
)
async def rebuild_index_route():
    """
    Kept for backward compatibility with older admin tooling.
    InsightFace embeddings are stored in Postgres with pgvector; there is no
    separate FAISS file to rebuild.
    """
    return await rebuild_face_index()
