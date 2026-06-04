import sys
import os
import time
import keyboard
import ctypes
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QWidget, QLabel, QSystemTrayIcon, QMenu, QStyle, QLineEdit, QHBoxLayout)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QIcon, QFont, QPixmap, QColor, QPainter

from capture import ScreenCapturer
from ocr import WindowsOCR
from translator import DeepTranslatorEngine
from overlay import SelectionOverlay, ResultOverlay
from audio_capture import AudioCapture
from audio_translator import AudioTranslator

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def get_env_path():
    """ Get the correct path for the .env file whether running as script or .exe """
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), ".env")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

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
    def __init__(self, start_selection_callback, start_voice_callback, exit_callback):
        super().__init__()
        self.exit_callback = exit_callback
        self.setWindowTitle("Realtime Translation")
        self.setWindowIcon(QIcon(get_resource_path("icon.png")))
        self.setFixedWidth(320)
        
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

        self.btn_select = QPushButton("Select Area (OCR)")
        self.btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select.clicked.connect(start_selection_callback)
        layout.addWidget(self.btn_select)
        
        self.btn_voice = QPushButton("Start Voice Translation")
        self.btn_voice.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_voice.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold; border-radius: 8px; padding: 10px;")
        self.btn_voice.clicked.connect(start_voice_callback)
        layout.addWidget(self.btn_voice)
        
        # --- API Setup Settings ---
        settings_label = QLabel("⚙️ Groq API Setup")
        settings_label.setStyleSheet("font-weight: bold; margin-top: 5px; font-size: 12px;")
        layout.addWidget(settings_label)
        
        tutorial = QLabel(
            "<a href='https://console.groq.com/keys' style='color: #89b4fa; text-decoration: none;'>Get your free API key here</a><br>"
            "<span style='color: #a6adc8; font-size: 10px;'>*Copy & save your key immediately! Groq will never show it again.</span>"
        )
        tutorial.setOpenExternalLinks(True)
        tutorial.setStyleSheet("font-size: 12px;")
        tutorial.setWordWrap(True)
        layout.addWidget(tutorial)
        
        api_layout = QHBoxLayout()
        api_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_save_api = QPushButton("💾")
        self.btn_save_api.setToolTip("Save API Key to .env")
        self.btn_save_api.setFixedSize(30, 28)
        self.btn_save_api.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_api.setStyleSheet("background-color: #45475a; color: #cdd6f4; border-radius: 4px; font-size: 14px;")
        self.btn_save_api.clicked.connect(self.save_api_key_manual)
        api_layout.addWidget(self.btn_save_api)
        
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Paste key(s) here...")
        from dotenv import load_dotenv
        env_path = get_env_path()
        load_dotenv(env_path)
        existing_keys = os.environ.get("GROQ_API_KEYS", os.environ.get("GROQ_API_KEY", ""))
        self.api_input.setText(existing_keys)
        self.api_input.setStyleSheet("background-color: #313244; color: #cdd6f4; border-radius: 4px; padding: 5px;")
        self.api_input.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        api_layout.addWidget(self.api_input)
        
        layout.addLayout(api_layout)
        
        if os.path.exists(env_path):
            warning = QLabel(".env saved locally! Keep it beside the .exe. NEVER share it.")
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #f38ba8; font-size: 10px; font-weight: bold;")
            layout.addWidget(warning)
            
            self.btn_open_env = QPushButton("Open .env Location")
            self.btn_open_env.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_open_env.setStyleSheet("background-color: #45475a; color: #cdd6f4; border-radius: 4px; padding: 5px; font-size: 11px;")
            self.btn_open_env.clicked.connect(self.open_env_location)
            layout.addWidget(self.btn_open_env)
        
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

    def save_api_key_manual(self):
        keys_text = self.api_input.text().strip()
        from dotenv import set_key
        import os
        env_path = get_env_path()
        if not os.path.exists(env_path):
            open(env_path, 'w').close()
        set_key(env_path, "GROQ_API_KEYS", keys_text)
        os.environ["GROQ_API_KEYS"] = keys_text
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(None, "Saved", "API Key saved successfully to .env!")

    def open_env_location(self):
        import subprocess
        env_path = get_env_path()
        if os.path.exists(env_path):
            # Open Windows Explorer and select the .env file
            subprocess.Popen(f'explorer /select,"{env_path}"')

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
        self.audio_capture = None
        self.audio_translator = AudioTranslator()
        
        self.control_panel = ControlPanel(self.start_selection, self.start_voice, self.exit_app)
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
        QTimer.singleShot(0, self.show_initial_window)
        sys.exit(self.app.exec())
        
    def show_initial_window(self):
        self.control_panel.showNormal()
        self.control_panel.activateWindow()
        
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
            "OCR Translation Started",
            "The app is running in the background. Press Ctrl+Alt+X to stop.",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

    def start_voice(self):
        keys_text = self.control_panel.api_input.text().strip()
        
        if not keys_text:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "API Key Required", "Please enter your Groq API Key before starting Voice Translation.")
            return
            
        if keys_text:
            from dotenv import set_key
            env_path = get_env_path()
            if not os.path.exists(env_path):
                open(env_path, 'w').close()
            set_key(env_path, "GROQ_API_KEYS", keys_text)
            os.environ["GROQ_API_KEYS"] = keys_text
            self.audio_translator.reload_keys()
            
            # Validate connection
            is_valid, error_msg = self.audio_translator.validate_keys()
            if not is_valid:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(None, "API Validation Failed", f"Groq Error: {error_msg}\n\nPlease check your API key and try again.")
                return

        self.control_panel.hide()
        
        # Stop existing threads if any
        if self.worker is not None:
            self.worker.stop()
        if self.audio_capture is not None:
            self.audio_capture.stop()
            
        self.result_overlay.show()
        self.result_overlay.update_text("Listening for Voice...\\n(Make sure game audio is playing)")
        
        self.audio_capture = AudioCapture(chunk_duration=4.0)
        # Connect capture to translator
        self.audio_capture.signals.audio_ready.connect(self.audio_translator.process_audio)
        # Connect translator to UI
        self.audio_translator.signals.translation_ready.connect(self.result_overlay.update_text)
        
        self.audio_capture.start()
        
        self.tray.showMessage(
            "Voice Translation Started",
            "Listening to PC audio. Press Ctrl+Alt+X to stop.",
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
            
        if self.audio_capture is not None:
            self.audio_capture.stop()
            self.audio_capture = None
            
        self.result_overlay.hide()
        self.selection_overlay.hide()
        
        self.control_panel.showNormal()
        self.control_panel.activateWindow()

    def exit_app(self):
        self.timer.stop()
        if self.worker is not None:
            self.worker.stop()
        if self.audio_capture is not None:
            self.audio_capture.stop()
        self.tray.hide()
        self.app.quit()
        # Ensure complete destruction to clean up keyboard hooks
        sys.exit(0)

if __name__ == "__main__":
    manager = AppManager()
    manager.start()
