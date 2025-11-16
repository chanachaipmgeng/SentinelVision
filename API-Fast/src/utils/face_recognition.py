import numpy as np
import face_recognition
from typing import List, Optional, Dict
from .liveness_detection import check_blink
from .image_quality import check_image_quality

def generate_face_encoding(image_path: str) -> Optional[List[float]]:
    """
    ตรวจสอบคุณภาพของภาพ อ่านภาพ และสร้าง Face Embedding
    """
    try:
        # 1. ตรวจสอบคุณภาพของภาพก่อน
        is_good, message = check_image_quality(image_path)
        if not is_good:
            raise ValueError(message)

        # 2. ถ้าคุณภาพดีแล้ว ค่อยโหลดภาพเพื่อทำ Face Recognition
        image = face_recognition.load_image_file(image_path)
        face_locations = face_recognition.face_locations(image)
        
        if not face_locations:
            return None
        
        # ใช้เฉพาะใบหน้าแรกที่เจอ
        face_encodings = face_recognition.face_encodings(image, face_locations)
        return face_encodings[0].tolist() # แปลงเป็น list ของ float

    except ValueError as ve:
        # Re-raise the specific quality error
        raise ve
    except Exception as e:
        print(f"Error generating face encoding: {e}")
        return None

def verify_liveness_and_get_encoding(image_paths: List[str]) -> Optional[List[float]]:
    """
    ตรวจสอบ Liveness และคืนค่า Encoding ของเฟรมที่เหมาะสมหาก Liveness ผ่าน
    """
    # --- Liveness Detection Step ---
    def get_landmarks(path):
        try:
            img = face_recognition.load_image_file(path)
            # ใช้ model='small' เพื่อความเร็วในการหา landmarks สำหรับ liveness
            locations = face_recognition.face_locations(img, model="cnn") 
            if not locations or len(locations) > 1:
                return None
            return face_recognition.face_landmarks(img, locations)[0]
        except Exception:
            return None

    face_landmarks_list = [get_landmarks(p) for p in image_paths]
    
    valid_landmarks = [lm for lm in face_landmarks_list if lm is not None]
    if len(valid_landmarks) < len(image_paths) / 2:
        raise ValueError("Face not consistently detected in frames.")

    is_live, reason = check_blink(valid_landmarks)
    if not is_live:
        raise ValueError(f"Liveness check failed: {reason}")
    
    # --- Face Encoding Step (after liveness is confirmed) ---
    # ใช้ภาพเฟรมกลางๆ ในการสร้าง Encoding เพื่อลดโอกาสที่จะได้ภาพตอนหลับตา
    image_to_recognize = image_paths[len(image_paths) // 2]
    
    encoding = generate_face_encoding(image_to_recognize)
    if encoding is None:
        raise ValueError("Could not generate face encoding from validation frame.")
        
    return encoding

def find_best_match(target_encoding: List[float], known_data: Dict[str, List[List[float]]], threshold: float) -> Optional[str]:
    """
    เปรียบเทียบ target_encoding กับ encodings ทั้งหมดของแต่ละบุคคล
    """
    if not known_data:
        return None

    np_target_encoding = np.array(target_encoding)
    overall_best_distance = float('inf')
    overall_best_label = None

    # วนลูปเพื่อหา memberId ที่มีระยะห่างน้อยที่สุด
    for member_id, encodings_for_member in known_data.items():
        if not encodings_for_member:
            continue

        # คำนวณระยะห่างของใบหน้าใหม่กับทุกๆ encoding ของ member คนนี้
        distances = np.linalg.norm(np.array(encodings_for_member) - np_target_encoding, axis=1)
        
        # เอาระยะห่างที่น้อยที่สุดของ member คนนี้
        best_distance_for_member = np.min(distances)

        # ถ้า member คนนี้มีระยะห่างน้อยกว่าคนที่เจอก่อนหน้า ให้เก็บค่าไว้
        if best_distance_for_member < overall_best_distance:
            overall_best_distance = best_distance_for_member
            overall_best_label = member_id

    print(f"Overall best match: {overall_best_label} with distance: {overall_best_distance:.4f}")

    # ตรวจสอบว่าระยะห่างที่น้อยที่สุดยังคงผ่านเกณฑ์ threshold หรือไม่
    if overall_best_distance < threshold:
        return overall_best_label
    else:
        return None
