from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QMessageBox, QDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QHBoxLayout
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt

from db import database # Import modul database yang sudah diupdate

class HistoryPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()
        self.loadHistory() # Memuat riwayat saat halaman diinisialisasi

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(20, 20, 20, 20) # Tambahkan margin

        # Header (Judul Halaman Riwayat)
        self.title = QLabel("📊 Riwayat Perjalanan")
        self.title.setFont(QFont('Arial', 24, QFont.Bold))
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("color: #333; margin-bottom: 20px;")
        self.layout.addWidget(self.title)

        # Ganti QListWidget dengan QTableWidget
        self.historyTable = QTableWidget()
        self.historyTable.setFont(QFont('Arial', 10))
        # Atur jumlah kolom dan header
        self.historyTable.setColumnCount(7) # ID, Mulai, Selesai, Jarak, Drowsy, Microsleep, Yawn
        self.historyTable.setHorizontalHeaderLabels([
            "ID Sesi", "Waktu Mulai", "Waktu Selesai", "Jarak (km)", "Drowsy", "Microsleep", "Menguap"
        ])
        
        # Sesuaikan lebar kolom agar memenuhi lebar tabel
        self.historyTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Nonaktifkan edit langsung pada sel
        self.historyTable.setEditTriggers(QTableWidget.NoEditTriggers)
        # Aktifkan pemilihan seluruh baris
        self.historyTable.setSelectionBehavior(QTableWidget.SelectRows)
        # Izinkan satu baris terpilih
        self.historyTable.setSelectionMode(QTableWidget.SingleSelection)

        self.historyTable.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #fff;
                gridline-color: #eee; /* Warna garis antar sel */
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #007bff; /* Biru cerah saat dipilih */
                color: white; /* Teks putih agar terlihat jelas */
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
        """)
        # Hubungkan double-click pada baris ke fungsi show_session_details
        self.historyTable.doubleClicked.connect(self.show_session_details_from_table)
        self.layout.addWidget(self.historyTable)

        # Tombol-tombol
        button_layout = QHBoxLayout()
        self.refreshButton = QPushButton("🔄 Refresh Riwayat")
        self.refreshButton.setFont(QFont('Arial', 12))
        self.refreshButton.setStyleSheet("background-color: #17a2b8; color: white; padding: 10px; border-radius: 5px;")
        self.refreshButton.clicked.connect(self.loadHistory)
        
        self.clearButton = QPushButton("🗑️ Bersihkan Semua Riwayat")
        self.clearButton.setFont(QFont('Arial', 12))
        self.clearButton.setStyleSheet("background-color: #dc3545; color: white; padding: 10px; border-radius: 5px;")
        self.clearButton.clicked.connect(self.confirm_clear_logs)

        self.backButton = QPushButton("🏠 Kembali ke Beranda")
        self.backButton.setFont(QFont('Arial', 12))
        self.backButton.setStyleSheet("background-color: #007bff; color: white; padding: 10px; border-radius: 5px;")
        self.backButton.clicked.connect(self.main_window.showHome)
        
        button_layout.addWidget(self.refreshButton)
        button_layout.addWidget(self.clearButton)
        button_layout.addWidget(self.backButton)
        
        self.layout.addLayout(button_layout)
        self.setLayout(self.layout)

    def loadHistory(self):
        """Memuat ringkasan sesi dari database dan menampilkannya dalam tabel."""
        self.historyTable.setRowCount(0) # Bersihkan tabel
        sessions = database.fetch_all_session_summaries() # Mengambil ringkasan sesi
        
        if not sessions:
            # Jika tidak ada sesi, tampilkan pesan di tabel
            # Untuk tabel, kita bisa membuat satu baris dan menggabungkan kolom
            self.historyTable.setRowCount(1)
            no_data_item = QTableWidgetItem("Belum ada riwayat perjalanan.")
            no_data_item.setTextAlignment(Qt.AlignCenter)
            no_data_item.setForeground(QColor("#6c757d"))
            self.historyTable.setSpan(0, 0, 1, self.historyTable.columnCount()) # Gabungkan semua kolom
            self.historyTable.setItem(0, 0, no_data_item)
            return

        self.historyTable.setRowCount(len(sessions)) # Set jumlah baris tabel
        
        for row_idx, session in enumerate(sessions):
            # session adalah objek sqlite3.Row, bisa diakses seperti dict
            session_id = session['session_id']
            start_time = session['start_time']
            end_time = session['end_time'] if session['end_time'] else "Belum Selesai"
            distance = session['total_distance_km']
            drowsy = session['drowsy_count']
            microsleep = session['microsleep_count']
            yawn = session['yawn_count']
            
            # Masukkan data ke dalam sel tabel
            self.historyTable.setItem(row_idx, 0, QTableWidgetItem(str(session_id)))
            self.historyTable.setItem(row_idx, 1, QTableWidgetItem(start_time))
            self.historyTable.setItem(row_idx, 2, QTableWidgetItem(end_time))
            self.historyTable.setItem(row_idx, 3, QTableWidgetItem(f"{distance:.2f}")) # Format jarak
            self.historyTable.setItem(row_idx, 4, QTableWidgetItem(str(drowsy)))
            self.historyTable.setItem(row_idx, 5, QTableWidgetItem(str(microsleep)))
            self.historyTable.setItem(row_idx, 6, QTableWidgetItem(str(yawn)))

            # Beri warna pada baris jika ada deteksi berbahaya
            # Ini akan mempengaruhi warna latar belakang sel, tapi seleksi akan menimpa ini
            if drowsy > 0 or microsleep > 0:
                for col in range(self.historyTable.columnCount()):
                    self.historyTable.item(row_idx, col).setBackground(QColor("#ffe0e0")) # Merah muda
            elif yawn > 0:
                for col in range(self.historyTable.columnCount()):
                    self.historyTable.item(row_idx, col).setBackground(QColor("#fffacd")) # Kuning muda
    
    def show_session_details_from_table(self):
        """Menampilkan detail log untuk sesi yang dipilih dari tabel."""
        selected_items = self.historyTable.selectedItems()
        if not selected_items:
            return # Tidak ada baris yang dipilih

        # Ambil session_id dari kolom pertama (indeks 0) dari baris yang dipilih
        row = selected_items[0].row()
        session_id = int(self.historyTable.item(row, 0).text())

        # Lanjutkan seperti fungsi show_session_details sebelumnya
        session_summary = database.get_last_session_summary(session_id)
        if not session_summary:
            QMessageBox.warning(self, "Error", "Detail sesi tidak ditemukan.")
            return

        logs = database.fetch_logs_for_session(session_id)
        
        detail_dialog = QDialog(self)
        detail_dialog.setWindowTitle(f"Detail Sesi ID: {session_id}")
        detail_dialog.setGeometry(200, 200, 800, 500)
        
        dialog_layout = QVBoxLayout()

        # Summary Info
        summary_label = QLabel(
            f"<b>Sesi Mulai:</b> {session_summary['start_time']}<br>"
            f"<b>Sesi Selesai:</b> {session_summary['end_time'] if session_summary['end_time'] else 'Belum Selesai'}<br>"
            f"<b>Total Jarak:</b> {session_summary['total_distance_km']:.2f} km<br>"
            f"<b>Mengantuk:</b> {session_summary['drowsy_count']}x | <b>Microsleep:</b> {session_summary['microsleep_count']}x | <b>Menguap:</b> {session_summary['yawn_count']}x"
        )
        summary_label.setFont(QFont('Arial', 10))
        dialog_layout.addWidget(summary_label)

        # Table for individual logs
        log_table = QTableWidget()
        # Perbarui jumlah kolom sesuai log Anda (log_id tidak perlu ditampilkan)
        log_table.setColumnCount(5) # timestamp, status_type, latitude, longitude, info
        log_table.setHorizontalHeaderLabels(["Timestamp", "Tipe Status", "Latitude", "Longitude", "Info"])
        log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) # Kolom menyesuaikan lebar
        log_table.setEditTriggers(QTableWidget.NoEditTriggers) # Tidak bisa diedit

        log_table.setRowCount(len(logs))
        for row_idx, log in enumerate(logs):
            log_table.setItem(row_idx, 0, QTableWidgetItem(log['timestamp']))
            log_table.setItem(row_idx, 1, QTableWidgetItem(log['status_type']))
            log_table.setItem(row_idx, 2, QTableWidgetItem(f"{log['latitude']:.6f}" if log['latitude'] else "-"))
            log_table.setItem(row_idx, 3, QTableWidgetItem(f"{log['longitude']:.6f}" if log['longitude'] else "-"))
            log_table.setItem(row_idx, 4, QTableWidgetItem(log['info'] if log['info'] else "-"))
        
        dialog_layout.addWidget(log_table)

        close_button = QPushButton("Tutup")
        close_button.clicked.connect(detail_dialog.accept)
        dialog_layout.addWidget(close_button)

        detail_dialog.setLayout(dialog_layout)
        detail_dialog.exec_() # Menampilkan dialog secara modal


    def confirm_clear_logs(self):
        """Konfirmasi sebelum menghapus semua log."""
        reply = QMessageBox.question(
            self,
            "Konfirmasi Hapus Riwayat",
            "Anda yakin ingin menghapus SEMUA riwayat perjalanan? Tindakan ini tidak dapat dibatalkan.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            database.clear_all_data()
            QMessageBox.information(self, "Berhasil", "Semua riwayat perjalanan telah dihapus.")
            self.loadHistory() # Muat ulang riwayat setelah dihapus

    def showEvent(self, event):
        """Dipanggil saat halaman ini ditampilkan."""
        super().showEvent(event)
        self.loadHistory() # Memuat ulang riwayat setiap kali halaman ini dibuka