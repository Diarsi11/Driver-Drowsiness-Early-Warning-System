from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class HomePage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        # Main Layout Vertikal
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 50, 50, 50) # Menambahkan margin agar tidak terlalu rapat
        layout.setAlignment(Qt.AlignCenter) # Pusatkan konten secara vertikal dan horizontal

        # Judul Aplikasi
        title = QLabel("Drowsiness Detection System")
        title.setFont(QFont('Arial', 32, QFont.Bold)) # Perbesar font
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;") # Warna teks gelap

        # Subtitle
        subtitle = QLabel("Pantau kondisi driver untuk perjalanan yang lebih aman.")
        subtitle.setFont(QFont('Arial', 14))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #7f8c8d; margin-bottom: 40px;") # Warna teks abu-abu

        # Tombol-tombol navigasi
        start_button = QPushButton("🚗 Mulai Deteksi Perjalanan")
        history_button = QPushButton("📊 Lihat Riwayat Perjalanan")
        
        # Styling tombol
        button_style = """
            QPushButton {
                background-color: #28a745; /* Hijau */
                color: white;
                padding: 15px 30px;
                font-size: 18px;
                border: none;
                border-radius: 8px;
                min-width: 250px; /* Lebar minimum */
                margin: 10px 0;
            }
            QPushButton:hover {
                background-color: #218838; /* Hijau lebih gelap saat hover */
            }
            QPushButton:pressed {
                background-color: #1e7e34; /* Hijau sangat gelap saat ditekan */
            }
        """
        history_button_style = """
            QPushButton {
                background-color: #007bff; /* Biru */
                color: white;
                padding: 15px 30px;
                font-size: 18px;
                border: none;
                border-radius: 8px;
                min-width: 250px;
                margin: 10px 0;
            }
            QPushButton:hover {
                background-color: #0056b3; /* Biru lebih gelap saat hover */
            }
            QPushButton:pressed {
                background-color: #004085; /* Biru sangat gelap saat ditekan */
            }
        """

        start_button.setStyleSheet(button_style)
        history_button.setStyleSheet(history_button_style)
        
        # Koneksi sinyal-slot
        start_button.clicked.connect(self.main_window.showLive)
        history_button.clicked.connect(self.main_window.showHistory)

        # Tambahkan widget ke layout
        layout.addStretch() # Dorong konten ke tengah
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(30) # Spasi antara subtitle dan tombol
        layout.addWidget(start_button, alignment=Qt.AlignCenter) # Pusatkan tombol
        layout.addWidget(history_button, alignment=Qt.AlignCenter) # Pusatkan tombol
        layout.addStretch() # Dorong konten ke tengah

        self.setLayout(layout)