from flask import Flask
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl
import sys

app = Flask(__name__)


class MMWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MagicMirror Display")
        self.setGeometry(100, 100, 1024, 768)
        # Create web view widget
        self.web = QWebEngineView(self)
        self.web.setUrl(QUrl("http://localhost:8080"))
        self.setCentralWidget(self.web)


def launch_gui():
    qt_app = QApplication(sys.argv)
    window = MMWindow()
    window.show()
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    launch_gui()
