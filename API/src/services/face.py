import cv2
if __name__ == '__main__':
    stored_face_path = r'D:\ProgectOut\DPU-Final-Project\final-project\API\src\uploads\bd8e8ca5-08ee-443a-8796-4a9b4e6bbddf.jpg' 
    # cv2.imshow("Display window", stored_face_path)
    stored_image = cv2.imread(stored_face_path)
    cv2.imshow("Display window", stored_image)