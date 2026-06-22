# pyqterminal

A lightweight, high-performance Python terminal emulator widget for PySide6/PyQt6.

It is built on top of the robust `libvterm` library and utilizes Cython for fast state parsing, combined with native `QPainter` for high-speed rendering. This project provides a fully native alternative to heavy WebEngine or JavaScript-based terminal components.

## Features

- **Fast rendering:** High-speed terminal drawing powered by a C/C++ backend (`libvterm`).
- **Native Qt Integration:** Written as a pure PySide6/PyQt6 widget using `QPainter`.
- **Lightweight:** Completely free of Web or Chromium dependencies.
- **Scrollback History:** Supports massive scrollback history natively.

## Installation

```bash
git clone https://github.com/hanyoukuang/pyqterminal.git
cd pyqterminal
pip install .
```

## Usage

See the `examples/` directory for usage details and examples of how to embed the terminal within your own applications.
