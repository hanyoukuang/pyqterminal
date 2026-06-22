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
        
        # Disable timer to simulate immediate update
        self.terminal._refresh_timer.stop()
        
        # Override write to call update directly
        original_write = self.terminal.write
        def new_write(data):
            original_write(data)
            if self.terminal.vt.dirty_rows:
                if self.terminal.scroll_offset > 0:
                    self.terminal.scroll_offset = 0
                self.terminal.update()
                self.terminal.vt.dirty_rows.clear()
        self.terminal.write = new_write

        self.decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        self.master_fd, self.slave_fd = pty.openpty()
        
        self.writer_thread = threading.Thread(target=self.blast_data)
        self.writer_thread.start()
            
        self.notifier = QSocketNotifier(self.master_fd, QSocketNotifier.Read)
        self.notifier.activated.connect(self.read_from_pty)
        
        self.start_time = time.time()
        self.bytes_read = 0
        
    def blast_data(self):
        data = b"A" * 80 + b"\r\n"
        chunk = data * 50
        for _ in range(250): # ~1MB
            os.write(self.slave_fd, chunk)
        os.close(self.slave_fd)

    def read_from_pty(self):
        try:
            data = os.read(self.master_fd, 4096)
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
headless.terminal.show()
app.exec()
