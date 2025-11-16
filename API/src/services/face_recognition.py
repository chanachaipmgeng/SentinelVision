import cv2
import sys
import numpy as np
import os
import pickle
def train_model():
    # ฝึกโมเดลด้วยภาพใบหน้าทั้งหมดใน dataset
    dataset_path = 'dataset'
    faces = []
    labels = []
    label_dict = {}
    current_label = 0
    print("trainModel")
    for employee_id in os.listdir(dataset_path):
        
        employee_folder = os.path.join(dataset_path, employee_id)
        print("train"+employee_folder)
        if not os.path.isdir(employee_folder):
            continue
        label_dict[current_label] = employee_id
        for image_name in os.listdir(employee_folder):
            image_path = os.path.join(employee_folder, image_name)
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                continue
            faces.append(image)
            labels.append(current_label)
        current_label += 1

    if len(faces) == 0:
        print("No faces found in dataset. Please add faces first.")
        return

    # สร้างและฝึกโมเดล
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(labels))

    # บันทึกโมเดลและป้ายกำกับ
    recognizer.save('trained_model.yml')
    with open('label_dict.pkl', 'wb') as f:
        pickle.dump(label_dict, f)

    print("Model trained and saved.")
    
# โหลด OpenCV Haar Cascade สำหรับการตรวจจับใบหน้า
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# อ่านพาธไฟล์รูปภาพจากพารามิเตอร์ที่ได้รับจาก Node.js
image_path = sys.argv[2]
action = sys.argv[1]  # 'add' สำหรับเพิ่มใบหน้า หรือ 'check' สำหรับตรวจสอบใบหน้า
employee_id = sys.argv[3]
if action == 'add':
    image = cv2.imread(image_path)
    if image is None:
        print("Error: Cannot load image")
        sys.exit(1)

    # แปลงภาพเป็นสีเทา
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # ตรวจจับใบหน้า
    faces = face_cascade.detectMultiScale(
        gray_image, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    if len(faces) == 0:
        print("No face detected")
        sys.exit(1)

    # ถ้าเจอใบหน้า ทำการตัดภาพใบหน้า
    x, y, w, h = faces[0]
    face = gray_image[y:y + h, x:x + w]
    face = cv2.resize(face, (200, 200))  # ปรับขนาดให้เท่ากัน

    # สร้างโฟลเดอร์สำหรับพนักงานถ้ายังไม่มี
    dataset_path = 'dataset'
    employee_folder = os.path.join(dataset_path, employee_id)
    if not os.path.exists(employee_folder):
        os.makedirs(employee_folder)

    # กำหนดชื่อไฟล์สำหรับเก็บภาพใบหน้า
    face_count = len(os.listdir(employee_folder))
    face_filename = os.path.join(employee_folder, f"{face_count+1}.jpg")
    cv2.imwrite(face_filename, face)
    train_model()
    print(face_filename)

elif action == 'check':
    if not os.path.exists('trained_model.yml') or not os.path.exists('label_dict.pkl'):
        print("Model not found. Please train the model first.")
        sys.exit(1)

    # โหลดโมเดลและป้ายกำกับ
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read('trained_model.yml')
    with open('label_dict.pkl', 'rb') as f:
        label_dict = pickle.load(f)

    # อ่านภาพจากไฟล์ที่ต้องการตรวจสอบ
    image = cv2.imread(image_path)
    if image is None:
        print("Error: Cannot load image")
        sys.exit(1)

    # แปลงภาพเป็นสีเทา
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # ตรวจจับใบหน้า
    faces = face_cascade.detectMultiScale(
        gray_image, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    if len(faces) == 0:
        print("No face detected in input image")
        sys.exit(1)

    # ตัดภาพใบหน้า
    x, y, w, h = faces[0]
    face = gray_image[y:y + h, x:x + w]
    face = cv2.resize(face, (200, 200))  # ปรับขนาดให้เท่ากัน

    # ทำนายใบหน้า
    label_id, confidence = recognizer.predict(face)
    
    # กำหนดเกณฑ์ความมั่นใจ
    threshold = 50.0  # ค่ายิ่งต่ำยิ่งแม่นยำ
    if confidence < threshold:
        empCheck = label_dict[label_id]
        if employee_id == empCheck :
            print(f"Face match found! : {employee_id} (confidence: {confidence})")
        else :
            print(f"Face Not match found! : {employee_id} : Match MemberId : { empCheck }(confidence: {confidence})")
        
    else:
        print(f"Face does not match (confidence: {confidence})")
else:
    print("Invalid action specified")
    sys.exit(1)

