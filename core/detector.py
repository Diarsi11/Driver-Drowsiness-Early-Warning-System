import os
import sys 
from ultralytics import YOLO
import cv2
import numpy as np
import mediapipe as mp
import time

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
    return os.path.join(base_path, relative_path)

class DrowsinessDetector:
    LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
    RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144] 

    CLASS_COLORS = {
        "awake": (0, 255, 0),     # Hijau
        "drowsy": (0, 0, 255),   # Merah
        "no_yawn": (255, 255, 0),# Kuning
        "yawn": (255, 0, 0),     # Biru
    }
    
    # Batas ambang EAR yang bisa disesuaikan
    EAR_THRESHOLD = 0.25 

    # --- AMBANG BATAS CONFIDENCE SPESIFIK PER KELAS ---
    CONFIDENCE_THRESHOLDS = {
        "drowsy": 0.5,   # Untuk deteksi kepala menunduk, dibuat lebih sensitif
        "yawn": 0.5,     # Untuk deteksi menguap
        "awake": 0.5,    # Untuk deteksi terjaga
        "no_yawn": 0.5,  # Untuk tidak menguap
    }

    def __init__(self, model_path='models/best.pt'):
        actual_model_path = resource_path(model_path)
        try:
            self.model = YOLO(actual_model_path)
            print("✅ YOLOv8 Model loaded successfully.")
            print("Using CPU for YOLOv8 inference (default).")
        except Exception as e:
            print(f"❌ ERROR: Failed to load YOLOv8 model from {actual_model_path}. Error: {e}")
            sys.exit(1) 


        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True, # Untuk landmark mata yang lebih detail
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        print("✅ MediaPipe Face Mesh initialized.")


    def calculate_ear(self, landmarks, eye_indices, img_w, img_h):
        """Menghitung Eye Aspect Ratio (EAR) dari landmarks mata."""
        p = [(int(landmarks[i].x * img_w), int(landmarks[i].y * img_h)) for i in eye_indices]

        # Konversi ke numpy array untuk perhitungan jarak
        p_np = np.array(p)
        
        # Jarak vertikal: P2-P6 dan P3-P5
        A = np.linalg.norm(p_np[1] - p_np[5]) # (P2 - P6)
        B = np.linalg.norm(p_np[2] - p_np[4]) # (P3 - P5)
        
        # Jarak horizontal: P1-P4
        C = np.linalg.norm(p_np[0] - p_np[3]) # (P1 - P4)
        
        ear = (A + B) / (2.0 * C)
        return ear

    def detect(self, frame: np.ndarray):
        """
        Melakukan deteksi YOLO dan EAR pada frame.
        Mengembalikan frame yang dianotasi dan dictionary hasil deteksi.
        """
        h, w, _ = frame.shape
        annotated_frame = frame.copy()
        
        # Inisialisasi status YOLO default.
        # Jika tidak ada deteksi yang memenuhi ambang batas per kelas, status akan tetap "awake".
        current_yolo_status = "awake" 
        current_ear_status = "unknown"
        avg_ear = None

        # 1. Deteksi YOLOv8
        results_yolo = self.model.predict(source=frame, conf=0.3, iou=0.4, verbose=False)[0] # Global conf set lower

        # Simpan deteksi yang valid untuk anotasi dan penentuan status
        valid_detections = [] 
        
        for box in results_yolo.boxes:
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            label = self.model.names[cls]
            
            if label in self.CONFIDENCE_THRESHOLDS and conf >= self.CONFIDENCE_THRESHOLDS[label]:
                valid_detections.append({'box': box, 'conf': conf, 'label': label})
        
        has_drowsy = False
        has_yawn = False
        has_no_yawn = False
        has_awake = False

        for det in valid_detections:
            x1, y1, x2, y2 = map(int, det['box'].xyxy[0])
            label = det['label']
            conf = det['conf']

            # Anotasi bounding box
            color = self.CLASS_COLORS.get(label, (255, 255, 255)) 
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                annotated_frame,
                f"{label} ({conf:.2f})",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )
            
            # Set flag untuk penentuan status utama
            if label == "drowsy":
                has_drowsy = True
            elif label == "yawn":
                has_yawn = True
            elif label == "no_yawn":
                has_no_yawn = True
            elif label == "awake":
                has_awake = True
        
        # Tentukan current_yolo_status berdasarkan prioritas tertinggi
        if has_drowsy:
            current_yolo_status = "drowsy"
        elif has_yawn:
            current_yolo_status = "yawn"
        elif has_no_yawn:
            current_yolo_status = "no_yawn"
        elif has_awake:
            current_yolo_status = "awake"

        # 2. Deteksi MediaPipe FaceMesh (untuk EAR)
        # Convert BGR to RGB untuk MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results_mp = self.face_mesh.process(rgb_frame)

        if results_mp.multi_face_landmarks:
            landmarks = results_mp.multi_face_landmarks[0]

            left_ear = self.calculate_ear(landmarks.landmark, self.LEFT_EYE_INDICES, w, h)
            right_ear = self.calculate_ear(landmarks.landmark, self.RIGHT_EYE_INDICES, w, h)
            avg_ear = (left_ear + right_ear) / 2.0

            ear_color = (255, 255, 0) # Kuning
            if avg_ear < self.EAR_THRESHOLD:
                current_ear_status = "microsleep"
                ear_color = (0, 0, 255) # Merah jika microsleep
                # Gambar lingkaran di mata untuk indikasi
                for i in self.LEFT_EYE_INDICES:
                    cv2.circle(annotated_frame, (int(landmarks.landmark[i].x * w), int(landmarks.landmark[i].y * h)), 2, ear_color, -1)
                for i in self.RIGHT_EYE_INDICES:
                    cv2.circle(annotated_frame, (int(landmarks.landmark[i].x * w), int(landmarks.landmark[i].y * h)), 2, ear_color, -1)
            else:
                current_ear_status = "eyes_open"
            
            cv2.putText(annotated_frame, f"EAR: {avg_ear:.3f}", (w - 150, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, ear_color, 2)
        else:
            current_ear_status = "no_face"
            cv2.putText(annotated_frame, "No Face Detected!", (w - 250, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2) # Oranye

        detection_results = {
            'yolo_status': current_yolo_status,
            'ear_status': current_ear_status,
            'avg_ear': avg_ear,
        }

        return annotated_frame, detection_results