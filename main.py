import sys
import os
import time
import keyboard
import ctypes
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QWidget, QLabel, QSystemTrayIcon, QMenu, QStyle)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QIcon, QFont, QPixmap, QColor, QPainter

from capture import ScreenCapturer
from ocr import WindowsOCR
from translator import DeepTranslatorEngine
from overlay import SelectionOverlay, ResultOverlay

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

class WorkerThread(QThread):
    result_signal = pyqtSignal(str)

    def __init__(self, rect, capturer, ocr_engine, translator):
        super().__init__()
        self.rect = rect
        self.capturer = capturer
        self.ocr_engine = ocr_engine
        self.translator = translator
        self.running = True
        self.last_text = ""

    def run(self):
        while self.running:
            x, y, w, h = self.rect
            
            # Avoid invalid rects
            if w <= 0 or h <= 0:
                time.sleep(0.5)
                continue
                
            image = self.capturer.capture_region(x, y, w, h)
            text = self.ocr_engine.extract_text(image)
            clean_text = text.strip()
            
            if clean_text and clean_text != self.last_text:
                self.last_text = clean_text
                print(f"Extracted OCR Text: '{clean_text}'")
                translated = self.translator.translate(clean_text)
                print(f"Translated Text: '{translated}'")
                self.result_signal.emit(translated)
                
            time.sleep(0.5)

    def stop(self):
        self.running = False
        self.wait()

class ControlPanel(QMainWindow):
    def __init__(self, start_selection_callback, exit_callback):
        super().__init__()
        self.exit_callback = exit_callback
        self.setWindowTitle("Realtime Translation")
        self.setWindowIcon(QIcon(get_resource_path("icon.png")))
        self.setFixedSize(300, 250)
        
        # Dark Theme Styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e2e;
            }
            QLabel {
                color: #cdd6f4;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #11111b;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton#exitBtn {
                background-color: #f38ba8;
            }
            QPushButton#exitBtn:hover {
                background-color: #eba0ac;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Realtime Translation")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(
            "1. Click 'Select Area'\n"
            "2. Draw a box over text\n"
            "3. Press Ctrl+Alt+X to Stop and return here"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        self.btn_select = QPushButton("Select Area")
        self.btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select.clicked.connect(start_selection_callback)
        layout.addWidget(self.btn_select)
        
        self.btn_exit = QPushButton("Exit App")
        self.btn_exit.setObjectName("exitBtn")
        self.btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exit.clicked.connect(exit_callback)
        layout.addWidget(self.btn_exit)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    def closeEvent(self, event):
        # When clicking the standard 'X' window button, exit completely
        self.exit_callback()
        event.accept()

class AppManager:
    def __init__(self):
        # Tell Windows this is a separate app from python.exe so the taskbar icon works properly
        myappid = 'RealtimeTranslation'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
        self.app = QApplication(sys.argv)
        self.app.setWindowIcon(QIcon(get_resource_path("icon.png")))
        # Prevent app from exiting automatically when Control Panel is hidden
        self.app.setQuitOnLastWindowClosed(False)
        
        self.capturer = ScreenCapturer()
        self.ocr = WindowsOCR()
        self.translator = DeepTranslatorEngine(source='en', target='id')
        
        self.selection_overlay = SelectionOverlay()
        self.result_overlay = ResultOverlay()
        
        self.worker = None
        
        self.control_panel = ControlPanel(self.start_selection, self.exit_app)
        self.setup_tray()
        
        self.selection_overlay.selection_made.connect(self.on_selection_made)
        
        # Setup Global Hotkey via QTimer to check thread-safely
        keyboard.add_hotkey('ctrl+alt+x', self.trigger_stop)
        self.stop_flag = False
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_flags)
        self.timer.start(100) # Check every 100ms
        
    def setup_tray(self):
        icon = QIcon(get_resource_path("icon.png"))
        self.tray = QSystemTrayIcon(icon, self.app)
        
        menu = QMenu()
        show_action = menu.addAction("Show Control Panel")
        show_action.triggered.connect(self.control_panel.showNormal)
        
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.exit_app)
        
        self.tray.setContextMenu(menu)
        self.tray.show()

    def start(self):
        self.control_panel.show()
        sys.exit(self.app.exec())
        
    def start_selection(self):
        self.control_panel.hide()
        self.selection_overlay.show()
        
    def on_selection_made(self, x, y, w, h):
        self.result_overlay.show()
        self.result_overlay.update_text(f"Selected Region: {w}x{h}\\nWaiting for text...")
        
        if self.worker is not None:
            self.worker.stop()
            
        self.worker = WorkerThread((x, y, w, h), self.capturer, self.ocr, self.translator)
        self.worker.result_signal.connect(self.result_overlay.update_text)
        self.worker.start()
        
        # Inform user we minimized to tray
        self.tray.showMessage(
            "Translation Started",
            "The app is running in the background. Press Ctrl+Alt+X to stop.",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

    def trigger_stop(self):
        self.stop_flag = True
        
    def check_flags(self):
        if self.stop_flag:
            self.stop_translation()
            self.stop_flag = False

    def stop_translation(self):
        if self.worker is not None:
            self.worker.stop()
            self.worker = None
            
        self.result_overlay.hide()
        self.selection_overlay.hide()
        
        self.control_panel.showNormal()
        self.control_panel.activateWindow()

    def exit_app(self):
        self.timer.stop()
        if self.worker is not None:
            self.worker.stop()
        self.tray.hide()
        self.app.quit()
        # Ensure complete destruction to clean up keyboard hooks
        sys.exit(0)

if __name__ == "__main__":
    manager = AppManager()
    manager.start()
