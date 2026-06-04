from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

class SelectionOverlay(QWidget):
    selection_made = pyqtSignal(int, int, int, int)
    
    def __init__(self):
        super().__init__()
        # Frameless, always on top, and works as a tool window so it doesn't show in taskbar
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Cover entire screen
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        self.begin = QPoint()
        self.end = QPoint()
        self.is_selecting = False
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100)) # Darken screen
        
        if self.is_selecting and not self.begin.isNull() and not self.end.isNull():
            rect = QRect(self.begin, self.end).normalized()
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent) # Clear the selected area
            
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            pen = QPen(QColor(0, 255, 0), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)
            
    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = event.pos()
        self.is_selecting = True
        self.update()
        
    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()
        
    def mouseReleaseEvent(self, event):
        self.is_selecting = False
        rect = QRect(self.begin, self.end).normalized()
        
        # Fix for Windows Display Scaling (High DPI):
        # PyQt uses logical pixels, but mss requires physical pixels.
        ratio = self.devicePixelRatioF()
        x = int(rect.x() * ratio)
        y = int(rect.y() * ratio)
        w = int(rect.width() * ratio)
        h = int(rect.height() * ratio)
        
        self.selection_made.emit(x, y, w, h)
        self.hide() # Hide instead of close so we can reuse if needed

class ResultOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.container = QWidget()
        self.container.setStyleSheet("""
            QWidget#container {
                background-color: rgba(0, 0, 0, 180);
                border-radius: 8px;
            }
            QLabel {
                color: #FFFFFF;
                padding: 10px;
            }
            QPushButton {
                background-color: transparent;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 20px;
                border: none;
                padding: 5px 15px;
            }
            QPushButton:hover {
                color: #AAAAAA;
            }
        """)
        self.container.setObjectName("container")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        
        self.header_layout = QHBoxLayout()
        self.header_layout.addStretch()
        self.toggle_btn = QPushButton("-")
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle_collapse)
        self.header_layout.addWidget(self.toggle_btn)
        
        self.label = QLabel("Waiting for text...")
        self.label.setWordWrap(True)
        self.label.setMinimumWidth(300)
        font = QFont("Arial", 16, QFont.Weight.Bold)
        self.label.setFont(font)
        
        self.container_layout.addLayout(self.header_layout)
        self.container_layout.addWidget(self.label)
        
        self.layout.addWidget(self.container)
        self.setLayout(self.layout)
        
        self.is_collapsed = False
        self.drag_pos = None
        
        # Put somewhere visible initially
        screen = QApplication.primaryScreen().geometry()
        self.move(int(screen.width() / 2 - 200), int(screen.height() - 250))
        
    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.label.hide()
            self.toggle_btn.setText("+")
        else:
            self.label.show()
            self.toggle_btn.setText("-")
        self.resize(0, 0) # Force window to shrink to minimum size hint
        self.adjustSize()
        
    def update_text(self, text):
        if not text:
            self.label.setText("No text found...")
        else:
            self.label.setText(text)
        if not self.is_collapsed:
            self.adjustSize()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()
