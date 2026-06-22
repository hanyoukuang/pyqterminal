from terminal import PyqTerminal
from PySide6.QtWidgets import QApplication

app = QApplication([])
t = PyqTerminal()
for i in range(50):
    t.write(f"Hello World {i}\n".encode('utf-8'))

# Now print history
for i in range(10, 15):
    line = t.vt.get_history_line(i)
    text = "".join(c['data'] for c in line)
    print(f"Row {i}: '{text.strip()}'")
