from scipy.spatial import distance as dist
import numpy as np

# ค่าคงที่สำหรับ Liveness Detection
EYE_AR_THRESH = 0.23  # ค่า Threshold สำหรับการหลับตา
EYE_AR_CONSEC_FRAMES = 2  # จำนวนเฟรมต่อเนื่องที่ต้องหลับตาเพื่อยืนยันการกระพริบ

def eye_aspect_ratio(eye):
    """
    คำนวณอัตราส่วนของดวงตา (Eye Aspect Ratio - EAR)
    eye: list ของ facial landmarks สำหรับดวงตาข้างหนึ่ง
    """
    # คำนวณระยะห่างแนวตั้งระหว่างเปลือกตาบนและล่าง
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])

    # คำนวณระยะห่างแนวนอนระหว่างหัวตาและหางตา
    C = dist.euclidean(eye[0], eye[3])

    # คำนวณ EAR
    ear = (A + B) / (2.0 * C)
    return ear

def check_blink(face_landmarks_list):
    """
    ตรวจสอบการกระพริบตาจาก list ของ facial landmarks ที่ได้จากหลายๆ เฟรม
    face_landmarks_list: list ของผลลัพธ์จาก face_recognition.face_landmarks()
    """
    if len(face_landmarks_list) < EYE_AR_CONSEC_FRAMES * 2:
        # ต้องการเฟรมอย่างน้อยสองเท่าของจำนวนเฟรมที่ต้องต่อเนื่องกัน
        return False, "Not enough frames for blink detection"

    blink_counter = 0
    total_blinks = 0

    left_eye_landmarks = [face['left_eye'] for face in face_landmarks_list]
    right_eye_landmarks = [face['right_eye'] for face in face_landmarks_list]

    for i in range(len(face_landmarks_list)):
        left_ear = eye_aspect_ratio(left_eye_landmarks[i])
        right_ear = eye_aspect_ratio(right_eye_landmarks[i])

        # ใช้ค่าเฉลี่ยของตาสองข้าง
        ear = (left_ear + right_ear) / 2.0

        if ear < EYE_AR_THRESH:
            blink_counter += 1
        else:
            # ถ้ามีการนับเฟรมที่หลับตาต่อเนื่องกันมา
            if blink_counter >= EYE_AR_CONSEC_FRAMES:
                total_blinks += 1
            # รีเซ็ตตัวนับ
            blink_counter = 0
    
    # ตรวจสอบครั้งสุดท้ายหลังจบ loop
    if blink_counter >= EYE_AR_CONSEC_FRAMES:
        total_blinks += 1

    if total_blinks > 0:
        return True, f"Blink detected ({total_blinks} blinks)"
    else:
        return False, "No blink detected"
