import time
from terminal import PyqTerminal
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPaintEvent
from PySide6.QtCore import QRect

app = QApplication([])
term = PyqTerminal()
term.show()

# Fill with data
data = ("A" * 80 + "\r\n") * 24
term.write(data)

t0 = time.time()
for _ in range(60):
    term.paintEvent(QPaintEvent(term.rect()))
t1 = time.time()

print(f"60 paintEvents took: {t1 - t0:.3f} seconds")
print(f"1 paintEvent = {(t1 - t0) / 60 * 1000:.1f} ms")
