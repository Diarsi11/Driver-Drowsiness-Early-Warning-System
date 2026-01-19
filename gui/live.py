import cv2
import time
import os
import sys
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QStackedWidget, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import QTimer, Qt, QUrl
from PyQt5.QtGui import QImage, QPixmap, QFont
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

from core.detector import DrowsinessDetector
from core.gps import GPS 
from db import database

# Fungsi pembantu untuk mendapatkan path aset di lingkungan PyInstaller
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
    return os.path.join(base_path, relative_path)


class LivePage(QWidget):
    # Konstanta untuk logika alarm
    MICROSLEEP_ALARM_THRESHOLD_SECONDS = 2
    DROWSY_ALARM_THRESHOLD_SECONDS = 2 
    YAWN_ALARM_THRESHOLD_SECONDS = 2 
    LOG_DEBOUNCE_SECONDS = 1.0 # Jeda minimal antar log untuk tipe event yang sama

    ALARM_SOUND_PATH = resource_path("assets/alarm.mp3")

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        # DrowsinessDetector akan secara internal menggunakan resource_path untuk modelnya
        self.detector = DrowsinessDetector(model_path='models/best.pt') 
        self.gps_tracker = GPS() # Inisialisasi GPS
        self.current_session_id = None # Untuk melacak sesi aktif
        self.session_start_time = None
        
        # Inisialisasi QMediaPlayer untuk alarm
        self.media_player = QMediaPlayer()
        # Set media content menggunakan ALARM_SOUND_PATH yang sudah disesuaikan
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(self.ALARM_SOUND_PATH)))
        self.media_player.setVolume(100) # Atur volume (0-100)
        self.media_player.mediaStatusChanged.connect(self._handle_media_status_changed) # Untuk loop
        
        # Debugging: Cetak path alarm yang digunakan
        print(f"✅ Alarm sound path: {self.ALARM_SOUND_PATH}")

        # Status deteksi real-time
        self.is_detecting = False
        self.capture = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        # Timer untuk logika alarm (reset)
        self.microsleep_start_time = None 
        self.drowsy_start_time = None     
        self.yawn_start_time = None       

        self.microsleep_logged = False
        self.drowsy_logged = False
        self.yawn_logged = False

        self.last_logged_microsleep_time = 0
        self.last_logged_drowsy_time = 0
        self.last_logged_yawn_time = 0

        # Penghitung deteksi per sesi
        self.current_drowsy_count = 0
        self.current_microsleep_count = 0
        self.current_yawn_count = 0
        self.current_awake_count = 0 # tidak ditampilkan pada UI. disimpan untuk konsistensi jika digunakan nanti
        self.current_no_yawn_count = 0 # tidak ditampilkan pada UI. disimpan untuk konsistensi jika digunakan nanti

        self.init_ui()

    def init_ui(self):
        # Main Layout: Vertikal
        main_layout = QVBoxLayout()
        
        # Header (Judul Halaman Live)
        header_label = QLabel("Deteksi Dini Kelelahan Mengemudi")
        header_label.setFont(QFont('Arial', 18, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        # Tambahkan margin-bottom yang lebih besar di sini untuk jarak dengan status
        header_label.setStyleSheet("margin-bottom: 25px; color: #333;")
        main_layout.addWidget(header_label)

        # Status Label (Dipindahkan ke sini)
        self.status_label = QLabel("Status: Menunggu...")
        self.status_label.setFont(QFont('Arial', 18, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)

        self.status_label.setStyleSheet("color: #555; margin-right: 250px;")
        self.status_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        main_layout.addWidget(self.status_label)
        
        # Video & Info Layout: Horizontal
        video_info_layout = QHBoxLayout()

        # Video Display (Kiri)
        video_panel_layout = QVBoxLayout()
        self.image_label = QLabel("Kamera Tidak Aktif")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #000; color: #FFF; border-radius: 5px;")
        self.image_label.setMinimumSize(640, 480) # Ukuran minimum untuk video
        video_panel_layout.addWidget(self.image_label)
        video_info_layout.addLayout(video_panel_layout, 3) # Beri bobot lebih besar ke video

        # Control & Stats Panel (Kanan)
        control_stats_panel_container = QWidget() 
        control_stats_panel_layout = QVBoxLayout(control_stats_panel_container)
        control_stats_panel_layout.setSpacing(10)
        
        control_stats_panel_container.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                padding: 15px;
                border-radius: 5px;
            }
        """)
        control_stats_panel_container.setMinimumWidth(300) 
        control_stats_panel_container.setMaximumWidth(400) 
        
        # Current Counts - NAMA LABEL DIUBAH
        self.drowsy_count_label = QLabel("Drowsy (Kepala Tunduk): 0") 
        self.microsleep_count_label = QLabel("Microsleep (Mata Terpejam): 0") 
        self.yawn_count_label = QLabel("Menguap: 0")
        self.distance_label = QLabel("Jarak Tempuh: 0.0 km") # Ini akan diupdate dari gps_tracker

        self.drowsy_count_label.setFont(QFont('Arial', 11))
        self.microsleep_count_label.setFont(QFont('Arial', 11))
        self.yawn_count_label.setFont(QFont('Arial', 11))
        self.distance_label.setFont(QFont('Arial', 11))

        control_stats_panel_layout.addWidget(self.drowsy_count_label)
        control_stats_panel_layout.addWidget(self.microsleep_count_label)
        control_stats_panel_layout.addWidget(self.yawn_count_label)
        control_stats_panel_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))
        control_stats_panel_layout.addWidget(self.distance_label)
        
        control_stats_panel_layout.addStretch(1) 

        # Control Buttons
        self.start_button = QPushButton("▶️ Mulai Deteksi")
        self.stop_button = QPushButton("⏹️ Berhenti Deteksi")
        self.back_button = QPushButton("🏠 Kembali ke Beranda")

        self.start_button.setStyleSheet("background-color: #28a745; color: white; padding: 10px; font-size: 14px; border-radius: 5px;")
        self.stop_button.setStyleSheet("background-color: #dc3545; color: white; padding: 10px; font-size: 14px; border-radius: 5px;")
        self.back_button.setStyleSheet("background-color: #007bff; color: white; padding: 10px; font-size: 14px; border-radius: 5px;")

        self.start_button.clicked.connect(self.start_detection)
        self.stop_button.clicked.connect(self.stop_detection)
        self.back_button.clicked.connect(self._go_home_safely)
        
        control_stats_panel_layout.addWidget(self.start_button)
        control_stats_panel_layout.addWidget(self.stop_button)
        control_stats_panel_layout.addWidget(self.back_button)
        
        self.stop_button.setEnabled(False) 
        self.back_button.setEnabled(True) 

        video_info_layout.addWidget(control_stats_panel_container, 1) 

        main_layout.addLayout(video_info_layout)
        main_layout.addStretch(1) 
        self.setLayout(main_layout)

    def _go_home_safely(self):
        """Memastikan deteksi dihentikan sebelum kembali ke beranda."""
        if self.is_detecting:
            self.stop_detection()
        self.main_window.showHome()

    def start_detection(self):
        if self.is_detecting:
            return

        print("Starting detection...")
        self.capture = cv2.VideoCapture(0)  # 0 = default webcam
        if not self.capture.isOpened():
            self.image_label.setText("Gagal membuka kamera.")
            print("ERROR: Could not open camera.")
            return

        self.is_detecting = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.back_button.setEnabled(False) 

        # Reset penghitung deteksi
        self.current_drowsy_count = 0
        self.current_microsleep_count = 0
        self.current_yawn_count = 0
        self.current_awake_count = 0
        self.current_no_yawn_count = 0
        
        self.microsleep_start_time = None
        self.drowsy_start_time = None
        self.yawn_start_time = None
        
        # Reset flag logging debounce
        self.last_logged_microsleep_time = 0
        self.last_logged_drowsy_time = 0
        self.last_logged_yawn_time = 0

        self._update_counts_display() 

        # Mulai sesi baru di database
        self.current_session_id = database.start_new_session()
        self.session_start_time = time.time()

        self.gps_tracker.start()
        self.timer.start(30) 
        self.status_label.setText("Status: Deteksi Aktif")
        self.status_label.setStyleSheet("color: #28a745; font-weight: bold;") 

    def stop_detection(self):
        if not self.is_detecting:
            return

        print("Stopping detection...")
        self.is_detecting = False
        self.timer.stop()
        if self.capture:
            self.capture.release()
            self.capture = None
        
        self.gps_tracker.stop() # MENGHENTIKAN THREAD GPS
        self.media_player.stop() 
        
        # Akhiri sesi di database
        if self.current_session_id:
            # Mengambil total jarak dari GPS tracker sebelum mengakhiri sesi
            total_distance = self.gps_tracker.get_total_distance_km() 
            # database modul ini sudah dimodifikasi agar DB_PATH benar
            database.end_session(self.current_session_id, total_distance)
            self.current_session_id = None 
            self.session_start_time = None

        self.image_label.clear()
        self.image_label.setText("Kamera Tidak Aktif")
        self.image_label.setStyleSheet("background-color: #000; color: #FFF; border-radius: 5px;")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.back_button.setEnabled(True) 
        self.status_label.setText("Status: Deteksi Dihentikan.")
        self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;") 

        # Reset alarm state dan flag logging
        self.microsleep_start_time = None
        self.drowsy_start_time = None
        self.yawn_start_time = None
        
        self.last_logged_microsleep_time = 0
        self.last_logged_drowsy_time = 0
        self.last_logged_yawn_time = 0
        
        print("Detection stopped.")

    def update_frame(self):
        if not self.capture or not self.capture.isOpened():
            self.stop_detection() 
            return

        ret, frame = self.capture.read()
        if not ret:
            self.stop_detection() 
            return
        
        frame = cv2.flip(frame, 1)

        # self.detector sudah menggunakan path yang benar secara internal
        annotated_frame, detection_results = self.detector.detect(frame)
        
        yolo_status = detection_results['yolo_status']
        ear_status = detection_results['ear_status']
        avg_ear = detection_results['avg_ear'] 

        current_time = time.time()
        
        # --- LOGIKA PENGHITUNGAN JARAK (MENGGUNAKAN GPS ASLI) ---
        if self.current_session_id:
            # Ambil jarak total dari gps_tracker yang sudah menghitungnya secara internal
            current_total_distance = self.gps_tracker.get_total_distance_km()
            self.distance_label.setText(f"Jarak Tempuh: {current_total_distance:.2f} km")
            self.current_distance_km = current_total_distance 

        # --- LOGIKA PENENTUAN STATUS & ALARM (TETAP SAMA) ---
        main_status_text = "Awake"
        main_status_color = "#28a745" # Hijau (Awake)
        play_alarm = False

        # === Logika untuk Microsleep (EAR) ===
        is_microsleep_ear = (ear_status == "microsleep")
        if is_microsleep_ear:
            if self.microsleep_start_time is None:
                self.microsleep_start_time = current_time
            
            elapsed_time_microsleep = current_time - self.microsleep_start_time
            
            if elapsed_time_microsleep >= self.MICROSLEEP_ALARM_THRESHOLD_SECONDS:
                play_alarm = True
                main_status_text = f"AWAS! Microsleep! ({int(elapsed_time_microsleep)}s)"

            if self.current_session_id and not self.microsleep_logged:
                if elapsed_time_microsleep >= self.MICROSLEEP_ALARM_THRESHOLD_SECONDS:
                    # database modul ini sudah dimodifikasi agar DB_PATH benar
                    database.log_detection_event(
                        self.current_session_id, 'microsleep',
                        *self.gps_tracker.get_location(), # MENGAMBIL LOKASI DARI GPS ASLI
                        info=f"Mata Terpejam. Durasi: {elapsed_time_microsleep:.1f}s, EAR: {avg_ear:.2f}"
                    )
                    database.update_session_counts(self.current_session_id, microsleep=1)
                    self.current_microsleep_count += 1
                    self.last_logged_microsleep_time = current_time
                    self.microsleep_logged = True  # Hindari log ulang
        else:
            self.microsleep_start_time = None
            self.microsleep_logged = False

        # === Logika untuk Drowsy (YOLO - Kepala Tunduk) ===
        is_drowsy_yolo = (yolo_status == "drowsy")
        if is_drowsy_yolo:
            if self.drowsy_start_time is None:
                self.drowsy_start_time = current_time
            
            elapsed_time_drowsy = current_time - self.drowsy_start_time

            if elapsed_time_drowsy >= self.DROWSY_ALARM_THRESHOLD_SECONDS:
                play_alarm = True
                main_status_text = f"AWAS! Drowsy (Kepala Tunduk)! ({int(elapsed_time_drowsy)}s)"

            if self.current_session_id and not self.drowsy_logged:
                if elapsed_time_drowsy >= self.DROWSY_ALARM_THRESHOLD_SECONDS:
                    # database modul ini sudah dimodifikasi agar DB_PATH benar
                    database.log_detection_event(
                        self.current_session_id, 'drowsy',
                        *self.gps_tracker.get_location(), # MENGAMBIL LOKASI DARI GPS ASLI
                        info=f"Kepala menunduk/miring. Durasi: {elapsed_time_drowsy:.1f}s"
                    )
                    database.update_session_counts(self.current_session_id, drowsy=1)
                    self.current_drowsy_count += 1
                    self.last_logged_drowsy_time = current_time
                    self.drowsy_logged = True
        else:
            self.drowsy_start_time = None
            self.drowsy_logged = False

        # === Logika untuk Yawn (YOLO) ===
        is_yawn_yolo = (yolo_status == "yawn")
        if is_yawn_yolo:
            if self.yawn_start_time is None:
                self.yawn_start_time = current_time
            
            elapsed_time_yawn = current_time - self.yawn_start_time

            if elapsed_time_yawn >= self.YAWN_ALARM_THRESHOLD_SECONDS:
                play_alarm = True
                main_status_text = f"AWAS! Menguap Berlebihan! ({int(elapsed_time_yawn)}s)"

            if self.current_session_id and not self.yawn_logged:
                if elapsed_time_yawn >= self.YAWN_ALARM_THRESHOLD_SECONDS:
                    # database modul ini sudah dimodifikasi agar DB_PATH benar
                    database.log_detection_event(
                        self.current_session_id, 'yawn',
                        *self.gps_tracker.get_location(), # MENGAMBIL LOKASI DARI GPS ASLI
                        info=f"Terdeteksi menguap. Durasi: {elapsed_time_yawn:.1f}s"
                    )
                    database.update_session_counts(self.current_session_id, yawn=1)
                    self.current_yawn_count += 1
                    self.last_logged_yawn_time = current_time
                    self.yawn_logged = True
        else:
            self.yawn_start_time = None
            self.yawn_logged = False


        # === Penentuan Status Tampilan Utama (Prioritas) ===
        # Prioritas: Alarm Merah > Peringatan Kuning > Normal Hijau/Biru
        if play_alarm:
            self.status_label.setStyleSheet(f"color: #dc3545; font-weight: bold;") # Merah jika ada alarm aktif
        elif is_microsleep_ear or is_drowsy_yolo or is_yawn_yolo:
            # Jika tidak ada alarm yang terpicu, tapi salah satu kondisi kelelahan masih ada
            # Ambil status yang paling 'parah' jika ada beberapa (misal: microsleep > drowsy > yawn)
            if is_microsleep_ear and self.microsleep_start_time is not None:
                elapsed = int(current_time - self.microsleep_start_time)
                main_status_text = f"Microsleep! ({elapsed}s)"
            elif is_drowsy_yolo and self.drowsy_start_time is not None:
                elapsed = int(current_time - self.drowsy_start_time)
                main_status_text = f"Drowsy (Kepala Tunduk)! ({elapsed}s)"
            elif is_yawn_yolo and self.yawn_start_time is not None:
                elapsed = int(current_time - self.yawn_start_time)
                main_status_text = f"Menguap... ({elapsed}s)"
            self.status_label.setStyleSheet(f"color: #ffc107; font-weight: bold;") # Kuning jika ada peringatan
        else: # Kondisi Normal
            if yolo_status == "awake" and ear_status == "eyes_open":
                main_status_text = "Awake & Eyes Open"
                main_status_color = "#28a745"
            elif yolo_status == "no_yawn" and ear_status == "eyes_open":
                main_status_text = "No Yawn & Eyes Open"
                main_status_color = "#17a2b8"
            elif ear_status == "no_face":
                main_status_text = "Wajah Tidak Terdeteksi!"
                main_status_color = "#6c757d"
            elif yolo_status == "unknown":
                main_status_text = "Menganalisis..."
                main_status_color = "#6c757d"
            self.status_label.setStyleSheet(f"color: {main_status_color}; font-weight: bold;")

        self.status_label.setText(f"Status: {main_status_text}")

        # Kontrol alarm audio
        if play_alarm and self.media_player.state() != QMediaPlayer.PlayingState:
            self.media_player.play()
            print("🔊 Alarm triggered!")
        elif not play_alarm and self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.stop()
            print("🔇 Alarm stopped.")

        self._update_counts_display() 

        # Tampilkan frame ke QLabel
        h, w, ch = annotated_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(annotated_frame.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(self.image_label.size(), 
                                                           Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)

    def _update_counts_display(self):
        """Memperbarui label hitungan di UI."""
        self.drowsy_count_label.setText(f"Drowsy (Kepala Tunduk): {self.current_drowsy_count}")
        self.microsleep_count_label.setText(f"Microsleep (Mata Terpejam): {self.current_microsleep_count}")
        self.yawn_count_label.setText(f"Menguap: {self.current_yawn_count}")
        # Jarak sudah diupdate langsung di update_frame

    def _handle_media_status_changed(self, status):
        """Callback untuk memutar ulang alarm jika selesai."""
        if status == QMediaPlayer.EndOfMedia:
            if self.is_detecting: 
                current_time = time.time()
                # Periksa apakah ada alarm yang masih harus aktif
                is_microsleep_alarm_active = (
                    self.microsleep_start_time is not None and 
                    (current_time - self.microsleep_start_time) >= self.MICROSLEEP_ALARM_THRESHOLD_SECONDS
                )
                is_drowsy_alarm_active = (
                    self.drowsy_start_time is not None and 
                    (current_time - self.drowsy_start_time) >= self.DROWSY_ALARM_THRESHOLD_SECONDS
                )
                is_yawn_alarm_active = (
                    self.yawn_start_time is not None and
                    (current_time - self.yawn_start_time) >= self.YAWN_ALARM_THRESHOLD_SECONDS
                )
                
                if is_microsleep_alarm_active or is_drowsy_alarm_active or is_yawn_alarm_active:
                    self.media_player.play()

    def showEvent(self, event):
        super().showEvent(event)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.stop_detection()