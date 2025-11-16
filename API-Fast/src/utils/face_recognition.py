import cv2
import numpy as np
import os
import face_recognition
import pickle
from concurrent.futures import ThreadPoolExecutor

# Paths
dataset_path = "dataset"
model_path = "face_encodings.pkl"

def load_model():
    """ โหลด embeddings จากไฟล์ pickle """
    if os.path.exists(model_path):
        with open(model_path, "rb") as f:
            return pickle.load(f)
    return {"encodings": [], "labels": {}}

def save_model(encodings, labels):
    """ บันทึก embeddings ลงไฟล์ pickle """
    with open(model_path, "wb") as f:
        pickle.dump({"encodings": encodings, "labels": labels}, f)

def get_face_embeddings(image_path):
    """ อ่านภาพและสร้าง Face Embedding """
    image = face_recognition.load_image_file(image_path)
    face_locations = face_recognition.face_locations(image)
    
    if len(face_locations) == 0:
        return None
    
    face_encodings = face_recognition.face_encodings(image, face_locations)
    return face_encodings[0]  # คืนค่า embedding แรกที่เจอ

def process_image(args):
    """ ใช้สำหรับ multi-threading """
    image_path, employeeId = args
    encoding = get_face_embeddings(image_path)
    return encoding, employeeId

def train_model():
    """ Train ใหม่ทั้งระบบ """
    print("Training model from scratch...")

    model_data = {"encodings": [], "labels": {}}
    image_paths = []
    labels = []

    for employeeId in os.listdir(dataset_path):
        employee_folder = os.path.join(dataset_path, employeeId)
        if not os.path.isdir(employee_folder):
            continue
        for image_name in os.listdir(employee_folder):
            image_paths.append(os.path.join(employee_folder, image_name))
            labels.append(employeeId)

    # ใช้ Multi-threading เพื่อเร่งการประมวลผล
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = executor.map(process_image, zip(image_paths, labels))

    for encoding, label in results:
        if encoding is not None:
            model_data["encodings"].append(encoding)
            model_data["labels"][len(model_data["encodings"]) - 1] = label

    save_model(model_data["encodings"], model_data["labels"])
    print("Model trained and saved.")

def update_model(image_path, employeeId):
    """ เพิ่มภาพใหม่ และอัปเดต Model โดยไม่ต้อง Train ใหม่ทั้งหมด """
    model_data = load_model()

    encoding = get_face_embeddings(image_path)
    if encoding is None:
        raise ValueError("No face detected")

    model_data["encodings"].append(encoding)
    model_data["labels"][len(model_data["encodings"]) - 1] = employeeId

    save_model(model_data["encodings"], model_data["labels"])
    print(f"Added new face for {employeeId} and updated model.")

def add_face_regonite(image_path, employeeId):
    """ เพิ่มใบหน้าเข้า dataset และอัปเดต model แบบ incremental """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("Error: Cannot load image")

    # บันทึกภาพ
    employee_folder = os.path.join(dataset_path, employeeId)
    os.makedirs(employee_folder, exist_ok=True)
    face_count = len(os.listdir(employee_folder))
    face_filename = os.path.join(employee_folder, f"{face_count+1}.jpg")
    cv2.imwrite(face_filename, image)

    # อัปเดต Model โดยไม่ต้อง Train ใหม่ทั้งหมด
    update_model(face_filename, employeeId)
    return face_filename

def check_face_regonite(image_path , employeeId, threshold=0.5):
    """ ตรวจสอบใบหน้าว่าตรงกับพนักงานคนไหน """
    if not os.path.exists(model_path):
        raise ValueError("Model not found. Please train the model first.")

    with open(model_path, "rb") as f:
        data = pickle.load(f)

    known_encodings = data["encodings"]
    labels = data["labels"]

    encoding = get_face_embeddings(image_path)
    if encoding is None:
        return "No face detected"

    # คำนวณ Euclidean Distance
    distances = np.linalg.norm(np.array(known_encodings) - encoding, axis=1)
    min_index = np.argmin(distances)

    # ตรวจสอบว่าใบหน้าใกล้เคียงกับฐานข้อมูลแค่ไหน
    if distances[min_index] < threshold:
        if employeeId == labels[min_index]:
            return f"Face match found! : {labels[min_index]} (Confidence: {distances[min_index]:.2f})"
        else:
            return f"Face not match! : {employeeId} : Match MemberId : {labels[min_index]} (confidence: {distances[min_index]:.2f})"
    else:
        return "Face does not match"
    
def check_face_regonite_emp(image_path, threshold=0.5):
    """ ตรวจสอบใบหน้าว่าตรงกับพนักงานคนไหน """
    if not os.path.exists(model_path):
        raise ValueError("Model not found. Please train the model first.")

    with open(model_path, "rb") as f:
        data = pickle.load(f)

    known_encodings = data["encodings"]
    labels = data["labels"]

    encoding = get_face_embeddings(image_path)
    if encoding is None:
        return "No face detected"

    # คำนวณ Euclidean Distance
    distances = np.linalg.norm(np.array(known_encodings) - encoding, axis=1)
    min_index = np.argmin(distances)

    # ตรวจสอบว่าใบหน้าใกล้เคียงกับฐานข้อมูลแค่ไหน
    if distances[min_index] < threshold:
        return labels[min_index]
    else:
        return "Face does not match"
