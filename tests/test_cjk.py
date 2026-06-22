from cyvterm import TerminalScreen

vt = TerminalScreen(5, 10)
vt.feed(b'\x1b[41m') # red background
vt.feed(b'\xe4\xb8\xad') # '中'
cells = [vt.get_cell(0, i) for i in range(3)]
for i, c in enumerate(cells):
    print(f"Cell {i}: data={repr(c['data'])}, width={c['width']}, bg={c['bg']}, fg={c['fg']}, reverse={c['reverse']}")
