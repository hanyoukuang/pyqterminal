import sys
import os
import pty
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSocketNotifier, QTimer
import time
from terminal import PyqTerminal
import codecs
import threading

class HeadlessPty:
    def __init__(self):
        self.terminal = PyqTerminal()
        self.terminal.resize(1920, 1080)
        self.terminal.cols = 200
        self.terminal.rows = 60
        self.decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        self.master_fd, self.slave_fd = pty.openpty()
        
        import fcntl
        flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
        fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        
        self.writer_thread = threading.Thread(target=self.blast_data)
        self.writer_thread.start()
            
        self.notifier = QSocketNotifier(self.master_fd, QSocketNotifier.Read)
        self.notifier.activated.connect(self.read_from_pty)
        
        self.start_time = time.time()
        self.bytes_read = 0
        
    def blast_data(self):
        data = b"A" * 200 + b"\r\n"
        chunk = data * 50
        for _ in range(1000): # ~1MB
            os.write(self.slave_fd, chunk)
        os.close(self.slave_fd)

    def read_from_pty(self):
        try:
            while True:
                try:
                    data = os.read(self.master_fd, 65536)
                    if data:
                        self.bytes_read += len(data)
                        text = self.decoder.decode(data)
                        if text:
                            self.terminal.write(text)
                    else:
                        self.finish()
                        break
                except BlockingIOError:
                    break
        except OSError:
            self.finish()
            
    def finish(self):
        end_time = time.time()
        print(f"Read {self.bytes_read} bytes in {end_time - self.start_time:.3f} seconds")
        QApplication.quit()

app = QApplication([])
headless = HeadlessPty()
headless.terminal.show()
app.exec()
