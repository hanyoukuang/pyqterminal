# pyqterminal API Reference

[中文版](API_zh.md) | [README](README.md)

A cross-platform terminal emulator widget with Rust-powered VT520 parsing and PySide6 rendering. Embed a fully functional terminal in your PySide6/PyQt6 application with a single widget.

## Installation

```bash
pip install pyqterminal
```

Requires Python ≥ 3.12. The Rust backend (`par-term-emu-core-rust`) is installed automatically.

## Quick Start

```python
import sys
from PySide6.QtWidgets import QApplication
from terminal import TerminalWidget

app = QApplication(sys.argv)

# Create an interactive terminal (spawns a shell)
widget = TerminalWidget(rows=40, cols=120)
widget.title_changed.connect(widget.setWindowTitle)
widget.show()
widget.start_shell()  # Starts the PTY shell

sys.exit(app.exec())
```

## Package Structure

```
terminal/
├── __init__.py          # Public API: TerminalWidget, InputHandler, __version__
├── __main__.py          # CLI entry point (pyqterminal command)
├── widget.py            # TerminalWidget — the terminal emulator widget
├── input_handler.py     # InputHandler — QKeyEvent → terminal bytes
└── py.typed             # PEP 561 type marker
```

Public imports:

```python
from terminal import TerminalWidget, InputHandler, __version__
```

---

## TerminalWidget

> `class TerminalWidget(parent=None, rows=24, cols=80, display_only=False, font_family=None, font_size=13)`

A PySide6 `QWidget` that renders a full terminal emulator. Two operating modes:

- **Interactive mode** (`display_only=False`, default) — spawns a real shell via PTY. Keyboard input is sent to the shell; output is rendered.
- **Display-only mode** (`display_only=True`) — no PTY. Feed escape sequences programmatically via `feed()`. Use for log viewers, SSH output displays, or ANSI art renderers.

### Constructor Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `parent` | `QWidget \| None` | `None` | Parent widget |
| `rows` | `int` | `24` | Initial terminal rows (auto-resizes with window) |
| `cols` | `int` | `80` | Initial terminal columns (auto-resizes with window) |
| `display_only` | `bool` | `False` | If `True`, uses headless `Terminal` (no PTY). Use `feed()` to push data. |
| `font_family` | `str \| None` | `None` | Font family name. If `None`, auto-detects from Nerd Font candidates. |
| `font_size` | `int` | `13` | Font size in points (range: 6–32 via zoom). |

### Properties

| Property | Type | Description |
|---|---|---|
| `rows` | `int` | Current number of visible rows |
| `cols` | `int` | Current number of visible columns |

### Methods

#### `start_shell() -> None`
Spawn an interactive shell via PTY. Only available in interactive mode (`display_only=False`). Raises `RuntimeError` in display-only mode.

```python
widget = TerminalWidget()
widget.start_shell()  # Launches $SHELL
```

#### `feed(data: str) -> None`
Feed escape sequences for rendering. Only available in display-only mode (`display_only=True`). Raises `RuntimeError` in interactive mode.

```python
widget = TerminalWidget(display_only=True)
widget.feed("\x1b[31mHello\x1b[0m\n")
widget.feed("\x1b[47m\x1b[30mBlack on white\x1b[0m\n")
```

#### `_change_font_size(delta: int) -> None`
Adjust font size by `delta` points (clamped to 6–32). Used internally by zoom shortcuts (Ctrl++ / Ctrl+- / Ctrl+0). Recalculates cell dimensions and triggers terminal resize.

```python
widget._change_font_size(2)   # Increase by 2pt
widget._change_font_size(-1)  # Decrease by 1pt
```

### Signals

All signals are `PySide6.QtCore.Signal`. Connect to them in embedding applications:

```python
widget.title_changed.connect(handle_title)
widget.process_exited.connect(handle_exit)
widget.bell_rang.connect(handle_bell)
```

#### `title_changed(str)`
Emitted when the shell changes the terminal window title (OSC escape sequences). The `str` parameter is the new title. In the built-in CLI, this is connected to `widget.setWindowTitle`.

```python
widget.title_changed.connect(lambda t: print(f"Title: {t}"))
```

#### `process_exited(int)`
Emitted when the shell process exits. The `int` parameter is the exit code. Connect to this to close the window or show a confirmation dialog.

```python
widget.process_exited.connect(lambda code: app.quit())
```

#### `bell_rang()`
Emitted when the terminal receives an ASCII BEL character (`\x07`). Use for visual or audio notifications.

```python
widget.bell_rang.connect(lambda: self.flash_window())
```

---

## InputHandler

> `class InputHandler`

Converts `PySide6.QtGui.QKeyEvent` objects into terminal input bytes. Used internally by `TerminalWidget.keyPressEvent()` but exposed for custom input handling.

### Class Method

#### `encode(event: QKeyEvent) -> bytes | None`
Encode a key event into terminal escape sequences. Returns `None` if the key should be ignored (modifier-only keys like Shift, Ctrl alone).

**Handles:**
- Plain text (including Unicode)
- Ctrl+key → C0 control codes (0x00–0x1F)
- Alt+key → ESC-prefixed sequences
- Special keys: arrows, home, end, page up/down, F1–F12, backspace, delete, insert, tab, escape
- Shift+Tab → `\x1b[Z`

```python
from terminal import InputHandler

def keyPressEvent(self, event):
    data = InputHandler.encode(event)
    if data:
        self.terminal.write(data)
```

**Platform notes:**
- macOS: Ctrl is mapped to `Qt.MetaModifier` (Cmd key). This means Cmd+C sends `\x03` (SIGINT) to the shell, matching macOS terminal conventions.
- Linux/Windows: Ctrl is `Qt.ControlModifier`.

---

## Usage Examples

### Embed in a PySide6 Application

```python
import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from terminal import TerminalWidget

class TerminalApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.terminal = TerminalWidget(display_only=False)
        self.terminal.title_changed.connect(self.setWindowTitle)
        self.terminal.process_exited.connect(self.close)
        self.setCentralWidget(self.terminal)
        self.resize(800, 600)
        self.terminal.start_shell()

app = QApplication(sys.argv)
window = TerminalApp()
window.show()
sys.exit(app.exec())
```

### Custom Font

```python
# Use a specific Nerd Font at 15pt
widget = TerminalWidget(font_family="JetBrainsMono Nerd Font", font_size=15)

# Auto-detect Nerd Font at 18pt
widget = TerminalWidget(font_size=18)
```

### Display-Only Mode (ANSI Art Viewer)

```python
widget = TerminalWidget(rows=30, cols=100, display_only=True)

# Feed ANSI escape sequences
widget.feed("\x1b[2J")                        # Clear screen
widget.feed("\x1b[1;1H")                      # Home cursor
widget.feed("\x1b[31mRed\x1b[0m \x1b[32mGreen\x1b[0m\n")
widget.feed("\x1b[1;33mBold Yellow\x1b[0m\n")
widget.feed("\x1b[4mUnderlined\x1b[0m\n")
widget.feed("\x1b[7mReverse video\x1b[0m\n")
```

### React to Shell Events

```python
widget = TerminalWidget()

def on_bell():
    QApplication.beep()  # System beep on terminal bell

def on_exit(code):
    print(f"Shell exited with code {code}")
    app.quit()

widget.bell_rang.connect(on_bell)
widget.process_exited.connect(on_exit)
widget.start_shell()
```

### Multi-Shell Tabbed Terminal (Conceptual)

```python
from PySide6.QtWidgets import QTabWidget

tabs = QTabWidget()
for i in range(3):
    term = TerminalWidget()
    term.title_changed.connect(
        lambda t, idx=i: tabs.setTabText(idx, t)
    )
    tabs.addTab(term, f"Shell {i+1}")
    term.start_shell()
```

---

## CLI Usage

After `pip install pyqterminal`:

```bash
# Interactive mode (spawns a shell)
pyqterminal

# Display-only mode (reads escape sequences from stdin)
echo -e '\x1b[31mHello\x1b[0m' | pyqterminal --display
ssh user@host 2>&1 | pyqterminal --display

# Version
pyqterminal --version
```

Keyboard shortcuts:

| Shortcut | Action |
|---|---|
| `Cmd+C` / `Ctrl+Shift+C` | Copy selection |
| `Cmd+V` / `Ctrl+Shift+V` | Paste |
| `Ctrl++` / `Ctrl+-` / `Ctrl+0` | Zoom in / out / reset |
| `Shift+PageUp` / `Shift+PageDown` | Scroll back / forward |
| Mouse drag | Select text (auto-copied on release) |
| Mouse wheel | Scroll |
| Middle-click | Paste |

## SGR Rendering Support

The terminal renders all major SGR (Select Graphic Rendition) attributes:

| SGR | Attribute | Rendering |
|---|---|---|
| 1 | Bold | `QFont.setBold(True)` |
| 2 | Dim | RGB halved (`c // 2`) |
| 3 | Italic | `QFont.setItalic(True)` |
| 4 | Underline | 5 styles: straight, double, curly, dotted, dashed |
| 5 | Blink | Text hidden on blink-off phase |
| 7 | Reverse | Foreground/background colors swapped |
| 8 | Hidden | Background only, no text |
| 9 | Strikethrough | Horizontal line at cell midpoint |
| 38;5;n | 256-color FG | 256-color palette |
| 48;5;n | 256-color BG | 256-color palette |
| 38;2;r;g;b | True Color FG | 24-bit RGB |
| 48;2;r;g;b | True Color BG | 24-bit RGB |
| CJK | Wide chars | Double-width cells (2 columns) |

---

## Font Detection

When `font_family=None`, the widget auto-detects the first available monospace font from this list (in order):

1. MesloLGS NF
2. JetBrainsMono Nerd Font
3. FiraCode Nerd Font
4. CaskaydiaCove Nerd Font
5. Hack Nerd Font
6. DejaVuSansMono Nerd Font
7. SF Mono
8. JetBrains Mono
9. Fira Code
10. Menlo
11. Courier New
12. monospace (system fallback)

For best rendering (Nerd Font icons in Powerlevel10k, oh-my-zsh themes), install a Nerd Font from [nerdfonts.com](https://www.nerdfonts.com/).

---

## Architecture

```
Interactive:  TerminalWidget → PtyTerminal (Rust, PTY + parser)
Display-only: TerminalWidget → Terminal     (Rust, parser only)
                  ├── InputHandler (QKeyEvent → terminal bytes)
                  └── QPainter     (direct paintEvent rendering)
```

Rendering pipeline:

```
Shell output → PTY → Rust vte parser → get_line_cells(row) → _render_cells() → QPainter
                                                                    │
                                                     reverse swap · dim · bold/italic
                                                     hidden · blink · wide char (2 cols)
                                                     strikethrough · underline (5 styles)
```
