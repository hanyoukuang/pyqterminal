from terminal import PyqTerminal
from PySide6.QtWidgets import QApplication

app = QApplication([])
t = PyqTerminal()
t.write(b"Line 1\nLine 2\n")
# Force scroll by writing enough lines
for i in range(100):
    t.write(f"Line {i+3}\n".encode('utf-8'))

# Now scroll offset
t._scroll_history(50)
print("History len:", t.vt.history_len())
print("Line -1 (history):", t.vt.get_history_line(t.vt.history_len() - 1)[0]['data'])
