"""Kai - A cross-platform terminal emulator with Rust backend and PySide6 frontend.

Usage:
  python main.py                    Interactive mode (default)
  python main.py --display          Display-only mode, reads from stdin
  echo -e '\\x1b[31mRED\\x1b[0m' | python main.py --display
"""

import sys
import argparse

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from terminal.widget import TerminalWidget


def main() -> None:
    parser = argparse.ArgumentParser(description="Kai Terminal Emulator")
    parser.add_argument("--display", action="store_true",
                        help="Display-only mode (reads escape sequences from stdin)")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("Kai")

    widget = TerminalWidget(rows=24, cols=80, display_only=args.display)
    widget.setWindowTitle("Kai" if not args.display else "Kai (display-only)")
    widget.resize(640, 480)
    widget.show()

    if args.display:
        # In display-only mode, read stdin and feed it to the terminal
        _start_display_mode(widget)
    else:
        # Interactive mode: start the shell once the event loop is running
        widget.start_shell()

    sys.exit(app.exec())


def _start_display_mode(widget: TerminalWidget) -> None:
    """Read from stdin and feed escape sequences to the display-only widget."""
    import os

    # Use a timer to read stdin non-blockingly in the Qt event loop
    data_buffer: list[str] = []

    def read_stdin() -> None:
        try:
            chunk = os.read(sys.stdin.fileno(), 4096)
            if chunk:
                widget.feed(chunk.decode("utf-8", errors="replace"))
            else:
                # stdin closed
                timer.stop()
        except (OSError, ValueError):
            timer.stop()

    timer = QTimer(widget)
    timer.timeout.connect(read_stdin)
    timer.start(50)  # Poll stdin every 50ms


if __name__ == "__main__":
    main()
