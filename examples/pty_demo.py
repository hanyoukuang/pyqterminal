import sys
import os
import pty
import fcntl
import termios
import struct
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QSocketNotifier, QTimer
from pyqterminal import PyqTerminal

import codecs

class PtyMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyqTerminal - zsh demo")
        self.resize(900, 600)
        
        self.terminal = PyqTerminal()
        self.setCentralWidget(self.terminal)
        
        # Fix UTF-8 boundary decoding issues
        self.decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        
        # Fork PTY
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            # Child process: spawn zsh
            os.execv('/bin/zsh', ['zsh'])
        
        # Set PTY fd to non-blocking
        flags = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        
        # Parent process: monitor the PTY master fd using QSocketNotifier (non-blocking!)
        self.notifier = QSocketNotifier(self.fd, QSocketNotifier.Read, self)
        self.notifier.activated.connect(self.read_from_pty)
        
        # Connect terminal interactions to PTY
        self.terminal.keyPressed.connect(self.write_to_pty)
        self.terminal.resized.connect(self.resize_pty)

        # Trigger initial resize to match widget window
        QTimer.singleShot(100, lambda: self.resize_pty(self.terminal.rows, self.terminal.cols))

    def read_from_pty(self):
        try:
            while True:
                try:
                    data = os.read(self.fd, 65536)
                    if data:
                        self.terminal.write(data)
                    else:
                        self.close()
                        break
                except BlockingIOError:
                    # No more data available right now
                    break
        except OSError:
            # PTY closed (e.g. user typed 'exit')
            self.notifier.setEnabled(False)
            self.close()

    def write_to_pty(self, text):
        os.write(self.fd, text.encode('utf-8'))

    def resize_pty(self, rows, cols):
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PtyMainWindow()
    window.show()
    sys.exit(app.exec())
