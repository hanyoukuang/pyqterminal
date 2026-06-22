from terminal import PyqTerminal
from PySide6.QtWidgets import QApplication

app = QApplication([])
t = PyqTerminal()
t.write(b"ABC\n")
t.write(b"DEF\n")
for i in range(100): t.write(b"\n")
print(t.vt.get_history_line(0)[:5])
