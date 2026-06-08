"""pyqterminal CLI entry point.

Usage:
  pyqterminal                        Interactive mode (default)
  pyqterminal --display              Display-only mode, reads from stdin
  echo -e '\\x1b[31mRED\\x1b[0m' | pyqterminal --display
"""

import argparse
import logging
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from terminal import __version__
from terminal.widget import TerminalWidget


def main() -> None:
    parser = argparse.ArgumentParser(
        description="pyqterminal — cross-platform terminal emulator",
    )
    parser.add_argument(
        "--display", action="store_true",
        help="Display-only mode (reads escape sequences from stdin)",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"pyqterminal {__version__}",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("pyqterminal")
    app.setApplicationDisplayName("pyqterminal")

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "pyqterminal")

    widget = TerminalWidget(rows=24, cols=80, display_only=args.display)
    widget.title_changed.connect(widget.setWindowTitle)
    widget.setWindowTitle(
        "pyqterminal" if not args.display else "pyqterminal (display-only)"
    )
    widget.resize(640, 480)
    widget.show()

    if args.display:
        _start_display_mode(widget)
    else:
        widget.start_shell()

    sys.exit(app.exec())


def _start_display_mode(widget: TerminalWidget) -> None:
    """Read from stdin and feed escape sequences to the display-only widget."""
    import os

    def read_stdin() -> None:
        try:
            chunk = os.read(sys.stdin.fileno(), 4096)
            if chunk:
                widget.feed(chunk.decode("utf-8", errors="replace"))
            else:
                timer.stop()
        except (OSError, ValueError):
            timer.stop()

    timer = QTimer(widget)
    timer.timeout.connect(read_stdin)
    timer.start(50)


if __name__ == "__main__":
    main()
