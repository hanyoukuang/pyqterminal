from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetricsF, QFontDatabase
from PySide6.QtCore import Qt, QRectF, QPointF

class W(QWidget):
    def __init__(self):
        super().__init__()
        self.font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.font.setPointSize(14)
        self.font.setStyleHint(QFont.Monospace)
        self.font.setFixedPitch(True)
        self.font.setKerning(False)
        self.setFont(self.font)
        
        m = QFontMetricsF(self.font)
        self.cw = m.horizontalAdvance("W")
        self.ch = m.height()
        self.a = m.ascent()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setFont(self.font)
        p.fillRect(e.rect(), QColor(0,0,0))
        p.setPen(QColor(255,255,255))
        p.drawText(QPointF(10.5, 10.5 + self.a), "Hello")
        
app = QApplication([])
w = W()
w.show()
app.exec()
