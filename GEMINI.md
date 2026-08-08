# Project Improvements by Gemini

This document tracks the major architectural and security improvements made to the DPU-Final-Project.

---

### 11. Full-stack Docker + nginx gateway (2026)

- **Description:** Packaged Web-Manage as a static nginx image; single **nginx** gateway on port 80 fronts admin (`/`) and FastAPI routes (same-origin `baseUrl: ''`). Employee mobile UI (`Webview-Mobile`) was later removed — check-in is admin kiosk only.
- **Benefit:** One `docker compose up --build` starts DB, API, admin UI, and reverse proxy.

---

### 1. Secure Liveness Detection (Backend & Frontend)

- **Description:** Implemented a secure, server-side liveness detection mechanism. The original client-side blink detection was removed to prevent security vulnerabilities.
- **Backend:** The API now accepts a sequence of images, performs a blink detection check (`check_blink`) on the server, and only proceeds if the check is successful. This prevents spoofing attacks using static photos or videos.
- **Frontend:** The Angular component (`face-scan.component.ts`) was refactored to capture a rapid sequence of 10 frames upon a user's click. This sequence is then sent to the backend for secure verification.
- **Benefit:** Greatly enhanced security by moving validation from the easily compromised client-side to the trusted server-side.

---

### 2. Database-centric Model Management

- **Description:** Re-architected the storage of face recognition data, moving it from a single, fragile `pickle` file (`face_encodings.pkl`) into the SQL database.
- **Implementation:**
  - Face encodings (128-dimension vectors) are now stored as JSON strings in the `faceEmbedding` column of the `Member` table.
  - The `face_recognition.py` utility was refactored to be a stateless calculation engine, completely decoupled from data storage.
  - The `face_controller.py` now orchestrates all database queries, fetching known encodings from the database for comparison during check-in.
- **Benefit:** Massively improved robustness, scalability, and maintainability. The system is no longer at risk from file corruption and can handle concurrent user enrollments safely.

---

### 3. Configurable Recognition Threshold

- **Description:** The hardcoded face recognition threshold (`0.5`) was made configurable.
- **Implementation:**
  - A new `config/settings.py` file was created to manage all project settings using Pydantic.
  - A `FACE_RECOGNITION_THRESHOLD` variable was added, which can be set via a `.env` file.
  - The face recognition controller now uses this value during the comparison process.
- **Benefit:** Allows administrators to easily "tune" the sensitivity (strictness vs. leniency) of the face recognition system without any code changes, adapting it to different environmental conditions.

---

### 4. Image Quality Check

- **Description:** Integrated a pre-processing step to validate image quality before attempting face recognition.
- **Implementation:**
  - Added configurable thresholds for blurriness and brightness to `config/settings.py`.
  - Created a new `utils/image_quality.py` utility to check if an image meets these criteria.
  - The `generate_face_encoding` function now performs this check first, raising a specific error if the image is too blurry, dark, or bright.
- **Benefit:** Improves system efficiency by avoiding processing of low-quality images and provides more specific error feedback to the user.

---

### 6. Secure Backend Geolocation Validation

- **Description:** Migrated the business logic for validating a user's GPS coordinates from the insecure client-side to the trusted backend.
- **Implementation:**
  - Created a `utils/geolocation.py` utility for Haversine distance calculation.
  - The `create_timestamp` controller now ignores the `timestampType` and `locationName` sent by the client.
  - It fetches allowed company locations from the database, calculates the distance, and overwrites the timestamp data with a server-verified location status before saving.
- **Benefit:** Closes a critical security vulnerability, preventing users from spoofing their location to check in from unauthorized areas. The timestamp data is now much more reliable.

---

### 7. Admin Face Encoding Management

- **Description:** Implemented a full-stack feature allowing administrators to view and delete enrolled face encodings for each user.
- **Backend:** Created new API endpoints (`GET /face/members/{memberId}/encodings` and `DELETE /face/encodings/{faceEncodingId}`) to support the frontend UI. The enrollment process was also updated to save the source image for display.
- **Frontend:** A new dialog component (`FaceManagementComponent`) was built in the `Web-Manage` application. This UI calls the new APIs to display each enrolled face as an image with a corresponding delete button, providing essential data management capability.
- **Benefit:** Gives administrators crucial control over the quality and accuracy of the face recognition data, allowing them to easily remove bad or incorrect enrollments.

---

### 8. High-Speed Search with FAISS

- **Description:** Replaced the linear, brute-force search for face matching with a highly optimized Approximate Nearest Neighbor (ANN) search using FAISS.
- **Implementation:**
  - A new utility `utils/face_index.py` was created to handle the building and searching of a FAISS index file from the database encodings.
  - A new admin endpoint `POST /system/rebuild-index` was created to trigger the index-building process on demand.
  - The `check_face_emp` controller now uses the FAISS index for near-instantaneous lookups instead of iterating through all database records.
- **Benefit:** Drastically improves the performance and scalability of the check-in process. Search time is now logarithmic (O(log N)) instead of linear (O(N)), ensuring the system remains fast even with tens of thousands of enrolled faces.

---

### 9. Reporting Dashboard

- **Description:** Implemented a full-stack dashboard feature for the admin web application to provide at-a-glance insights into attendance data.
- **Backend:** A new `GET /dashboard/stats/{companyId}` endpoint was created to efficiently query and aggregate key statistics, including daily check-ins, 7-day trends, and recent activities.
- **Frontend:** A new `DashboardComponent` was built using `ngx-echarts` to visualize data. The UI now displays summary cards, a 7-day trend chart, and a table of recent check-ins, turning raw data into actionable business intelligence.
- **Benefit:** Provides significant business value by allowing administrators and managers to easily monitor and analyze attendance patterns.

---

- **Implementation:**
  - Created a new `FaceEncoding` table with a one-to-many relationship to the `Member` table.
  - The `add_face` function now saves each new enrollment as a separate record in the `FaceEncoding` table.
  - The `find_best_match` algorithm was upgraded to handle the new data structure. It now finds the best possible match against a user's entire gallery of encodings before comparing with other users.
- **Benefit:** The system is now much more tolerant to variations in lighting, angle, and facial expression, drastically reducing false negative matches.

---

