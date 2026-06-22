import sys
import os
import pty
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSocketNotifier, QTimer
import time
from terminal import PyqTerminal
import codecs

class HeadlessPty:
    def __init__(self):
        self.terminal = PyqTerminal()
        self.decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.execv('/bin/bash', ['bash', '-c', 'base64 /dev/urandom | head -c 1000000'])
            
        self.notifier = QSocketNotifier(self.fd, QSocketNotifier.Read)
        self.notifier.activated.connect(self.read_from_pty)
        
        self.start_time = time.time()
        self.bytes_read = 0

    def read_from_pty(self):
        try:
            data = os.read(self.fd, 4096)
            if data:
                self.bytes_read += len(data)
                text = self.decoder.decode(data)
                if text:
                    self.terminal.write(text)
            else:
                self.finish()
        except OSError:
            self.finish()
            
    def finish(self):
        end_time = time.time()
        print(f"Read {self.bytes_read} bytes in {end_time - self.start_time:.3f} seconds")
        QApplication.quit()

app = QApplication([])
headless = HeadlessPty()
app.exec()
