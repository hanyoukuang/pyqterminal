"""pyqterminal - A cross-platform terminal emulator with Rust backend and PySide6 frontend."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("pyqterminal")
except PackageNotFoundError:
    __version__ = "0.0.0"

from terminal.widget import TerminalWidget
from terminal.input_handler import InputHandler

__all__ = ["TerminalWidget", "InputHandler", "__version__"]
