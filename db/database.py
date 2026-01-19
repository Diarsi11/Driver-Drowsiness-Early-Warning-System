import sqlite3
import os # Tambahkan impor os
import sys # Tambahkan impor sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional

# Fungsi pembantu untuk mendapatkan path aset/data di lingkungan PyInstaller
def get_resource_path(relative_path: str) -> Path:
    """
    Mendapatkan path absolut ke sumber daya (resource), berfungsi untuk lingkungan
    pengembangan dan untuk PyInstaller.

    Untuk database, kita ingin database berada di lokasi yang dapat ditulis
    oleh pengguna, seperti folder AppData di Windows.
    """
    if getattr(sys, 'frozen', False):
        # Jika berjalan dari PyInstaller EXE
        # Gunakan AppData untuk menyimpan database agar persisten dan dapat ditulis
        app_data_dir = os.path.join(os.environ.get('APPDATA', ''), "DrowsinessDetectionApp")
        
        # Buat direktori jika belum ada
        os.makedirs(app_data_dir, exist_ok=True)
        return Path(app_data_dir) / relative_path
    else:
        db_folder = Path(__file__).parent
        db_folder.mkdir(parents=True, exist_ok=True)
        return db_folder / relative_path

# Gunakan fungsi get_resource_path untuk menentukan DB_PATH
DB_PATH = get_resource_path("detection_history.db")

# --- MODIFIKASI BERAKHIR DI SINI ---


def get_db_connection():
    """Mendapatkan koneksi database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    """Membuat tabel jika belum ada."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Tabel untuk ringkasan setiap sesi perjalanan
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_summary (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                total_distance_km REAL DEFAULT 0.0,
                drowsy_count INTEGER DEFAULT 0,
                microsleep_count INTEGER DEFAULT 0,
                yawn_count INTEGER DEFAULT 0,
                awake_count INTEGER DEFAULT 0,
                no_yawn_count INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Active' -- 'Active' or 'Completed'
            )
        ''')
        # Tabel untuk log setiap kejadian deteksi spesifik
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detection_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                status_type TEXT NOT NULL, -- 'drowsy', 'microsleep', 'yawn', 'awake', 'no_yawn'
                latitude REAL,
                longitude REAL,
                info TEXT, -- Tambahan informasi, misal durasi microsleep
                FOREIGN KEY (session_id) REFERENCES session_summary (session_id)
            )
        ''')
        conn.commit()
    print(f"✅ Database initialized at: {DB_PATH}")

def start_new_session() -> int:
    """Memulai sesi deteksi baru dan mengembalikan session_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        start_time = datetime.now().isoformat(sep=' ', timespec='seconds')
        cursor.execute('''
            INSERT INTO session_summary (start_time, status)
            VALUES (?, ?)
        ''', (start_time, 'Active'))
        conn.commit()
        session_id = cursor.lastrowid
    print(f"🆕 Started new session with ID: {session_id}")
    return session_id

def end_session(session_id: int, total_distance_km: float):
    """Mengakhiri sesi deteksi dan mengupdate ringkasan."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        end_time = datetime.now().isoformat(sep=' ', timespec='seconds')
        cursor.execute('''
            UPDATE session_summary
            SET end_time = ?, total_distance_km = ?, status = ?
            WHERE session_id = ?
        ''', (end_time, total_distance_km, 'Completed', session_id))
        conn.commit()
    print(f"✅ Session {session_id} ended and updated.")

def update_session_counts(
    session_id: int,
    drowsy: int = 0,
    microsleep: int = 0,
    yawn: int = 0,
    awake: int = 0,
    no_yawn: int = 0
):
    """Mengupdate hitungan status deteksi untuk sesi aktif."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE session_summary
            SET drowsy_count = drowsy_count + ?,
                microsleep_count = microsleep_count + ?,
                yawn_count = yawn_count + ?,
                awake_count = awake_count + ?,
                no_yawn_count = no_yawn_count + ?
            WHERE session_id = ?
        ''', (drowsy, microsleep, yawn, awake, no_yawn, session_id))
        conn.commit()

def log_detection_event(
    session_id: int,
    status_type: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    info: Optional[str] = None
):
    """
    Mencatat satu kejadian deteksi (drowsy, microsleep, yawn, dll) ke detection_log.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat(sep=' ', timespec='seconds')
        cursor.execute('''
            INSERT INTO detection_log (session_id, timestamp, status_type, latitude, longitude, info)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session_id, timestamp, status_type, latitude, longitude, info))
        conn.commit()


def fetch_all_session_summaries() -> List[sqlite3.Row]:
    """Mengambil semua ringkasan sesi."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM session_summary ORDER BY start_time DESC')
        return cursor.fetchall()

def fetch_logs_for_session(session_id: int) -> List[sqlite3.Row]:
    """Mengambil semua log deteksi untuk sesi tertentu."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM detection_log WHERE session_id = ? ORDER BY timestamp ASC', (session_id,))
        return cursor.fetchall()

def get_last_session_summary(session_id: int) -> Optional[sqlite3.Row]:
    """Mengambil ringkasan sesi terakhir berdasarkan ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM session_summary WHERE session_id = ?', (session_id,))
        return cursor.fetchone()

def clear_all_data():
    """Menghapus semua data dari semua tabel (untuk reset atau debug)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM detection_log')
        cursor.execute('DELETE FROM session_summary')
        conn.commit()
    print("🗑️ All database data cleared.")

# Inisialisasi database saat modul dimuat
init_db()