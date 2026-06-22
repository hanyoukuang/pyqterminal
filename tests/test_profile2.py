import time
from terminal import PyqTerminal
from PySide6.QtWidgets import QApplication

app = QApplication([])
term = PyqTerminal()

data = ("A" * 80 + "\r\n") * 50
chunks = 250

t0 = time.time()
for _ in range(chunks):
    term.write(data)
t1 = time.time()

print(f"Total time: {t1 - t0:.3f} seconds")
