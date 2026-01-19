import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt5.QtCore import Qt

# Import halaman-halaman GUI
from gui.home import HomePage
from gui.live import LivePage
from gui.history import HistoryPage

from db import database

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drowsiness Detection System")
        self.setGeometry(100, 100, 1200, 800)

        self.setStyleSheet("background-color: #f8f9fa;")

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Inisialisasi halaman-halaman
        self.home_page = HomePage(self)
        self.live_page = LivePage(self)
        self.history_page = HistoryPage(self)

        # Tambahkan halaman ke stacked widget
        self.stacked_widget.addWidget(self.home_page)      # Index 0
        self.stacked_widget.addWidget(self.live_page)      # Index 1
        self.stacked_widget.addWidget(self.history_page)   # Index 2

        self.showHome()

        # Inisialisasi database
        database.init_db()
        print("Application started. Database initialized.")

    def showHome(self):
        """Menampilkan halaman Home."""
        self.stacked_widget.setCurrentWidget(self.home_page)
        self.setWindowTitle("Drowsiness Detection System - Beranda")

    def showLive(self):
        """Menampilkan halaman Live Detection."""
        self.stacked_widget.setCurrentWidget(self.live_page)
        self.setWindowTitle("Drowsiness Detection System - Deteksi Langsung")

    def showHistory(self):
        """Menampilkan halaman Riwayat Deteksi."""
        self.stacked_widget.setCurrentWidget(self.history_page)
        self.setWindowTitle("Drowsiness Detection System - Riwayat Deteksi")
    
    def closeEvent(self, event):
        """
        Overrides the close event to ensure camera and resources are released.
        """
        print("Closing application...")

        if self.live_page.is_detecting:
            self.live_page.stop_detection()
        
        super().closeEvent(event)
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Atur font default aplikasi
    font = QApplication.font()
    font.setPointSize(10)
    app.setFont(font)

    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())