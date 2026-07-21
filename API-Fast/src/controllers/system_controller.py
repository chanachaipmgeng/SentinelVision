async def rebuild_face_index():
    """
    FAISS rebuild is no longer required — embeddings live in Postgres (pgvector)
    and are searchable immediately after enroll/delete.
    """
    return {
        "message": (
            "No rebuild needed. Face search uses pgvector cosine distance "
            "on face_encoding.embedding (InsightFace 512-d)."
        ),
        "index": "pgvector",
    }
