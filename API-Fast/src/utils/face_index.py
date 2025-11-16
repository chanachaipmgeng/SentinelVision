import faiss
import numpy as np
import os
import json
import pickle
from sqlalchemy.future import select

from ..config.database import get_db
from ..models.face_encoding import FaceEncoding

INDEX_PATH = "face_index.faiss"
ID_MAP_PATH = "face_index_id_map.pkl"

async def build_and_save_index():
    """
    ดึงข้อมูล Encoding ทั้งหมดจาก DB มาสร้างและบันทึก FAISS index
    """
    print("Building and saving FAISS index...")
    db_gen = get_db()
    db = await db_gen.__anext__()
    try:
        stmt = select(FaceEncoding.faceEncodingId, FaceEncoding.encoding)
        result = await db.execute(stmt)
        all_encodings = result.fetchall()

        if not all_encodings:
            print("No face encodings in the database to index.")
            # If index files exist, remove them
            if os.path.exists(INDEX_PATH):
                os.remove(INDEX_PATH)
            if os.path.exists(ID_MAP_PATH):
                os.remove(ID_MAP_PATH)
            return

        # Prepare data for FAISS
        db_ids = [enc.faceEncodingId for enc in all_encodings]
        vectors = np.array([json.loads(enc.encoding) for enc in all_encodings]).astype('float32')
        
        dimension = vectors.shape[1]  # Should be 128
        index = faiss.IndexFlatL2(dimension)
        index.add(vectors)

        # Save the index and the ID mapping
        faiss.write_index(index, INDEX_PATH)
        with open(ID_MAP_PATH, 'wb') as f:
            pickle.dump(db_ids, f)

        print(f"Successfully built and saved index with {index.ntotal} vectors.")

    finally:
        await db.close()

def search_face(target_encoding: list, threshold: float) -> (str, str):
    """
    ค้นหาใบหน้าที่คล้ายที่สุดจาก FAISS index และคืนค่า memberId
    """
    if not os.path.exists(INDEX_PATH) or not os.path.exists(ID_MAP_PATH):
        raise RuntimeError("Index file not found. Please build the index first.")

    # Load the index and the ID mapping
    index = faiss.read_index(INDEX_PATH)
    with open(ID_MAP_PATH, 'rb') as f:
        db_ids = pickle.load(f)

    # Prepare target vector
    target_vector = np.array([target_encoding]).astype('float32')

    # Search the index for the 1 nearest neighbor
    D, I = index.search(target_vector, 1)
    
    distance = D[0][0]
    index_position = I[0][0]

    if index_position == -1:
        return None, None # No match found

    print(f"FAISS search found best match with distance: {distance:.4f}")

    if distance < threshold:
        # The ID returned by FAISS is the position in the original list
        face_encoding_id = db_ids[index_position]
        return face_encoding_id, distance
    else:
        return None, None
