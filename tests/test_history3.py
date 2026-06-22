from terminal import PyqTerminal
from PySide6.QtWidgets import QApplication
import cyvterm

app = QApplication([])
t = PyqTerminal()
t.write(b"ABC\n")
print("Raw line length:", len(t.vt._history[0][1]))
print("Cols:", t.vt._history[0][0])
