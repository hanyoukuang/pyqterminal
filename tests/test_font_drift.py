import sys
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QFont, QFontMetrics, QPainter
from PySide6.QtCore import Qt

class TestWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.font = QFont("Monaco", 14)
        self.font.setStyleHint(QFont.Monospace)
        self.font.setFixedPitch(True)
        self.font.setKerning(False)
        self.font.setStyleStrategy(QFont.ForceIntegerMetrics)
        self.metrics = QFontMetrics(self.font)
        self.char_width = self.metrics.horizontalAdvance("W")
        self.resize(800, 200)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(self.font)
        
        # Draw 60 'A's grouped
        text = "A" * 60
        painter.drawText(0, 30, text)
        
        # Draw 60 'A's individually, 10 pixels below
        for i in range(60):
            painter.drawText(i * self.char_width, 60, "A")
            
        # Draw a red line at the end of where 60 chars SHOULD be
        painter.setPen(Qt.red)
        painter.drawLine(60 * self.char_width, 0, 60 * self.char_width, 100)

app = QApplication(sys.argv)
w = TestWidget()
w.show()
app.exec()
