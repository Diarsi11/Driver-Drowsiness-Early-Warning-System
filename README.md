# 🚗 Driver Drowsiness Early Warning System  
### (YOLOv8 & MediaPipe EAR)

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![YOLOv8](https://img.shields.io/badge/Model-YOLOv8s-green.svg)](https://ultralytics.com)
[![MediaPipe](https://img.shields.io/badge/Framework-MediaPipe-red.svg)](https://mediapipe.dev)
[![Database](https://img.shields.io/badge/Database-SQLite3-lightgrey.svg)](https://www.sqlite.org/)

Sistem **Peringatan Dini Kantuk Pengemudi (Real-Time)** yang menggabungkan **Deep Learning (YOLOv8)** dan **Computer Vision (MediaPipe EAR)**.  
Proyek ini dirancang untuk mendeteksi gejala kelelahan pengemudi secara akurat melalui analisis visual wajah guna meminimalisir risiko kecelakaan lalu lintas.

---

## 🌟 Fitur Utama

- **Deteksi Microsleep**  
  Menggunakan perhitungan *Eye Aspect Ratio (EAR)* melalui **MediaPipe Face Mesh** untuk mendeteksi mata tertutup dengan presisi tinggi.

- **Deteksi Ekspresi (Menguap & Tertunduk)**  
  Menggunakan model **YOLOv8s** yang telah dilatih khusus untuk klasifikasi kondisi wajah secara real-time.

- **Sistem Riwayat (History Logging)**  
  Integrasi database **SQLite3** (`detection_history.db`) untuk mencatat waktu, durasi, dan jenis gejala kantuk.

- **Aplikasi Desktop GUI**  
  Dibangun menggunakan **PyQt5** dengan tampilan dashboard yang informatif dan mudah digunakan.

- **Audio & Visual Alert**  
  Sistem alarm otomatis berbasis suara dan indikator visual ketika pengemudi terdeteksi dalam kondisi berbahaya.

---

## 🛠️ Teknologi & Library

- **YOLOv8 (Ultralytics)** – Model utama deteksi kondisi wajah  
- **MediaPipe** – Ekstraksi 468 facial landmarks & perhitungan EAR  
- **PyQt5** – Framework aplikasi desktop  
- **OpenCV & NumPy** – Pengolahan video dan komputasi visual  
- **SQLite3** – Penyimpanan data riwayat  
- **Dataset (Roboflow)**  
  https://app.roboflow.com/tes-lcnzw/drowsy-eme21/models

---

## 📊 Detail Model & Dataset

- **Jumlah Dataset**: 3.132 gambar  
- **Kelas**: `awake`, `drowsy`, `yawn`, `no_yawn`  
- **Arsitektur**: YOLOv8s  
- **Training**: 100 Epoch  
- **Performa**: **mAP@50 ≈ 90%**

---

## ⚙️ Konfigurasi Kamera (Webcam)

Secara default aplikasi menggunakan kamera internal laptop (**index 0**).  
Untuk menggunakan webcam eksternal, ubah konfigurasi berikut:

```python
print("Starting detection...")
self.capture = cv2.VideoCapture(0)  # 0 = default webcam

if not self.capture.isOpened():
    self.image_label.setText("Gagal membuka kamera.")
    print("ERROR: Could not open camera.")
    return
```

**Ganti menjadi:**

```python
# Gunakan index 1 atau 2 jika memakai webcam eksternal
self.capture = cv2.VideoCapture(1) 
```

## 🚀 Instalasi & Penggunaan

1. **Clone Repository**
```bash
git clone https://github.com/username/project-name.git
cd project-name
```
2. **Instal Dependensi**
```bash
pip install -r requirements.txt
```
3. **Jalankan Aplikasi**
```bash
python main.py
```
## 📂 Struktur Proyek

```text
├── core/                 # Logika deteksi (YOLO + MediaPipe EAR)
├── gui/                  # Antarmuka PyQt5
├── models/               # Bobot model YOLOv8 (best.pt)
├── assets/               # Audio alarm & ikon
├── detection_history.db  # Database lokal (auto-generate)
└── main.py               # Entry point aplikasi
```
## 📌 Rencana Pengembangan (Future Works)

* **Optimasi Hardware**
  Porting ke Raspberry Pi atau Jetson Nano.

* **Notifikasi IoT**
  Integrasi API pihak ketiga untuk pengiriman lokasi pengemudi.

* **Sensor Fusion**
  Penggabungan data visual dengan sensor detak jantung (wearable device).
