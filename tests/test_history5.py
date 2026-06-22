from terminal import PyqTerminal
from PySide6.QtWidgets import QApplication
import cyvterm

app = QApplication([])
t = PyqTerminal()
t.write(b"ABC\n")
