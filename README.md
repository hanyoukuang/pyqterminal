# Kai

A cross-platform terminal emulator — Python frontend, Rust backend.

<p align="center">
  <img src="screenshot.png" alt="Kai Terminal Screenshot" width="720">
</p>

## Features

- 🦀 **Rust-powered TUI** — parses VT520 escape sequences via the `vte` crate
- 🎨 **Full SGR support** — bold, italic, underline (5 styles: straight, double, curly, dotted, dashed), reverse video, dim, blink, strikethrough, hidden text
- 🌐 **CJK** — proper double-width rendering for Chinese, Japanese, Korean
- 🔣 **Nerd Font** — renders icon glyphs (Powerlevel10k, oh-my-zsh themes)
- 🖱️ **Mouse** — text selection with auto-copy, right-click context menu, scrollback with wheel
- 📋 **Clipboard** — Cmd+C / Cmd+V (macOS), Ctrl+Shift+C / Ctrl+Shift+V (Linux/Windows)
- 🔍 **Zoom** — Ctrl++/-/0 adjust font size (6–32pt)
- ⚡ **No buffering** — renders directly via QPainter, no QPixmap double-buffer (Retina-safe)
- 🪟 **Cross-platform** — macOS, Linux, Windows

## Installation

Requires Python 3.12.13+ and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/hanyoukuang/kai.git
cd kai
uv sync
```

## Usage

```bash
uv run python main.py
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

## Architecture

```
main.py → TerminalWidget (QWidget) → PtyTerminal (Rust backend)
            ├── InputHandler      (QKeyEvent → terminal bytes)
            └── QPainter           (direct paintEvent rendering)
```

- **Backend:** [`par-term-emu-core-rust`](https://github.com/paulrobello/par-term-emu-core-rust) — Rust `vte` crate handles PTY, escape parsing, buffer, colors, cursor, scrollback
- **Frontend:** PySide6 `QPainter` — renders directly in `paintEvent()`, no QPixmap double-buffer (avoids Retina/HiDPI issues)
- **Input:** `InputHandler` maps `QKeyEvent` to terminal escape sequences

### Rendering pipeline

```
Shell output → PTY → Rust vte parser → get_line_cells(row) → _render_cells() → QPainter
                                                                    │
                                                     reverse swap · dim · bold/italic
                                                     hidden · blink · wide char (2 cols)
                                                     strikethrough · underline (5 styles)
```

## License

MIT © 2026 Kaihong Han
