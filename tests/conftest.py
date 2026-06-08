"""Shared pytest fixtures for pyqterminal tests."""

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication — required for QPainter, QKeyEvent, etc."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Do not quit — session-scoped, let pytest cleanup handle it
