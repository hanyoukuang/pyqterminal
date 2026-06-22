import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from pyqterminal import PyqTerminal

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyqTerminal MVP Test")
        self.resize(700, 500)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Initialize terminal widget
        self.terminal = PyqTerminal()
        self.layout.addWidget(self.terminal)
        
        self.btn = QPushButton("Simulate ANSI Data Stream")
        self.btn.clicked.connect(self.run_test)
        self.layout.addWidget(self.btn)
        
    def run_test(self):
        self.terminal.clear()
        
        # Basic text
        self.terminal.write("Welcome to \033[1;36mPyqTerminal\033[0m MVP!\r\n")
        self.terminal.write("=====================================\r\n\n")
        self.terminal.write("\033[32m[中文测试]\033[0m 这是一个全角字符对齐的测试！\r\n")
        self.terminal.write("123456789012345678901234567890123456\r\n\n")
        
        # ANSI Colors
        self.terminal.write("Color Test:\r\n")
        self.terminal.write("  \033[31m[Red]\033[0m \033[32m[Green]\033[0m \033[33m[Brown]\033[0m \033[34m[Blue]\033[0m \033[35m[Magenta]\033[0m \033[36m[Cyan]\033[0m\r\n")
        self.terminal.write("  \033[41m Red BG \033[0m \033[42m Green BG \033[0m \033[44m Blue BG \033[0m\r\n")
        self.terminal.write("  \033[7m Reverse Video \033[0m\r\n\n")
        
        # Carriage return test (overwrite)
        self.terminal.write("Progress: [          ]\r")
        self.terminal.write("Progress: [=====     ]\r")
        self.terminal.write("Progress: [==========] Done!\r\n\n")

        # More advanced features
        self.terminal.write("Advanced Features:\r\n")
        self.terminal.write("  \033[4mUnderlined Text\033[0m, \033[1mBold Text\033[0m, \033[3mItalic Text\033[0m, \033[9mStrikethrough\033[0m\r\n")
        
        self.terminal.write("\r\n256 Colors Test:\r\n")
        for i in range(16, 36):
            self.terminal.write(f"\033[48;5;{i}m  \033[0m")
        self.terminal.write("\r\n")

        self.terminal.write("\r\nTrueColor (RGB) Test:\r\n")
        self.terminal.write("  \033[38;2;255;100;100mTrue\033[38;2;100;255;100mColor \033[38;2;100;100;255mSupport\033[0m\r\n\n")

        self.terminal.write("Try selecting this text with your mouse and press Ctrl+C to copy!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
