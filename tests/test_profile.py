import time
from cyvterm import TerminalScreen

vt = TerminalScreen(24, 80)
# Create 1MB of text
data = b"A" * 80 + b"\r\n"
chunk = data * 50  # ~4KB
chunks = 250 # ~1MB

t0 = time.time()
for _ in range(chunks):
    vt.feed(chunk)
t1 = time.time()

print(f"Total time: {t1 - t0:.3f} seconds")
