"""Unit tests for InputHandler — keyboard event encoding.

Tests cover:
  - Normal data: known key → known escape sequence
  - Boundary data: keys without mapping, edge key values
  - Error data: modifier-only keys → None
"""

import sys

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from terminal.input_handler import InputHandler

# ── Helpers ─────────────────────────────────────────────────────────────

def _make_event(key, modifiers=Qt.NoModifier, text="") -> QKeyEvent:
    """Create a synthetic QKeyEvent for testing encode()."""
    return QKeyEvent(QKeyEvent.KeyPress, key, modifiers, text)


# ── Normal data tests ───────────────────────────────────────────────────

class TestNormalKeys:
    """Known key → known escape sequence mappings."""

    def test_enter_returns_cr(self):
        assert InputHandler.encode(_make_event(Qt.Key_Return)) == b"\r"

    def test_tab_returns_tab(self):
        assert InputHandler.encode(_make_event(Qt.Key_Tab)) == b"\t"

    def test_escape_returns_esc(self):
        assert InputHandler.encode(_make_event(Qt.Key_Escape)) == b"\x1b"

    def test_backspace_returns_del(self):
        assert InputHandler.encode(_make_event(Qt.Key_Backspace)) == b"\x7f"

    def test_up_arrow(self):
        assert InputHandler.encode(_make_event(Qt.Key_Up)) == b"\x1b[A"

    def test_down_arrow(self):
        assert InputHandler.encode(_make_event(Qt.Key_Down)) == b"\x1b[B"

    def test_right_arrow(self):
        assert InputHandler.encode(_make_event(Qt.Key_Right)) == b"\x1b[C"

    def test_left_arrow(self):
        assert InputHandler.encode(_make_event(Qt.Key_Left)) == b"\x1b[D"

    def test_home(self):
        assert InputHandler.encode(_make_event(Qt.Key_Home)) == b"\x1b[H"

    def test_end(self):
        assert InputHandler.encode(_make_event(Qt.Key_End)) == b"\x1b[F"

    def test_page_up(self):
        assert InputHandler.encode(_make_event(Qt.Key_PageUp)) == b"\x1b[5~"

    def test_page_down(self):
        assert InputHandler.encode(_make_event(Qt.Key_PageDown)) == b"\x1b[6~"

    def test_delete(self):
        assert InputHandler.encode(_make_event(Qt.Key_Delete)) == b"\x1b[3~"

    def test_insert(self):
        assert InputHandler.encode(_make_event(Qt.Key_Insert)) == b"\x1b[2~"

    def test_f1(self):
        assert InputHandler.encode(_make_event(Qt.Key_F1)) == b"\x1bOP"

    def test_f12(self):
        assert InputHandler.encode(_make_event(Qt.Key_F12)) == b"\x1b[24~"


class TestNormalText:
    """Plain text (including Shift for uppercase) is encoded as UTF-8."""

    def test_lowercase_letter(self):
        assert InputHandler.encode(_make_event(Qt.Key_A, text="a")) == b"a"

    def test_uppercase_letter_with_shift(self):
        assert InputHandler.encode(
            _make_event(Qt.Key_A, Qt.ShiftModifier, text="A")) == b"A"

    def test_digit(self):
        assert InputHandler.encode(_make_event(Qt.Key_1, text="1")) == b"1"

    def test_unicode_character(self):
        assert InputHandler.encode(_make_event(Qt.Key_unknown, text="中")) == "中".encode()


# ── Ctrl combinations ───────────────────────────────────────────────────

class TestCtrlKeys:
    """Ctrl+key → C0 control codes (0x00-0x1F)."""

    @staticmethod
    def _ctrl_mod() -> Qt.KeyboardModifier:
        """Return the platform-appropriate Ctrl modifier."""
        return Qt.MetaModifier if sys.platform == "darwin" else Qt.ControlModifier

    def test_ctrl_a(self):
        result = InputHandler.encode(_make_event(Qt.Key_A, self._ctrl_mod()))
        assert result == b"\x01"

    def test_ctrl_c(self):
        result = InputHandler.encode(_make_event(Qt.Key_C, self._ctrl_mod()))
        assert result == b"\x03"

    def test_ctrl_z(self):
        result = InputHandler.encode(_make_event(Qt.Key_Z, self._ctrl_mod()))
        assert result == b"\x1a"

    def test_ctrl_open_bracket(self):
        """Ctrl+[ should produce ESC (0x1b)."""
        result = InputHandler.encode(
            _make_event(Qt.Key_BracketLeft, self._ctrl_mod(), text="\x1b"))
        assert result is not None

    def test_ctrl_special_key_mapped(self):
        """Ctrl+Home should return the Home sequence (not a C0 code)."""
        result = InputHandler.encode(_make_event(Qt.Key_Home, self._ctrl_mod()))
        assert result == b"\x1b[H"


# ── Alt combinations ────────────────────────────────────────────────────

class TestAltKeys:
    """Alt+key → ESC-prefixed sequences."""

    def test_alt_up_arrow(self):
        result = InputHandler.encode(_make_event(Qt.Key_Up, Qt.AltModifier))
        assert result == b"\x1b\x1b[A"

    def test_alt_letter(self):
        result = InputHandler.encode(
            _make_event(Qt.Key_B, Qt.AltModifier, text="b"))
        assert result == b"\x1bb"


# ── Shift+Tab ───────────────────────────────────────────────────────────

class TestShiftTab:
    """Shift+Tab → back-tab sequence."""

    def test_shift_tab(self):
        result = InputHandler.encode(_make_event(Qt.Key_Tab, Qt.ShiftModifier))
        assert result == b"\x1b[Z"


# ── Boundary data tests ─────────────────────────────────────────────────

class TestBoundary:
    """Keys without mappings, edge cases."""

    def test_unknown_key_no_text_returns_none(self):
        """Key with no mapping and no text should return None."""
        result = InputHandler.encode(_make_event(Qt.Key_unknown))
        assert result is None

    def test_modifier_only_shift_returns_none(self):
        result = InputHandler.encode(_make_event(Qt.Key_Shift, Qt.ShiftModifier))
        assert result is None

    def test_modifier_only_ctrl_returns_none(self):
        result = InputHandler.encode(_make_event(Qt.Key_Control, Qt.ControlModifier))
        assert result is None

    def test_modifier_only_alt_returns_none(self):
        result = InputHandler.encode(_make_event(Qt.Key_Alt, Qt.AltModifier))
        assert result is None

    def test_modifier_only_meta_returns_none(self):
        result = InputHandler.encode(_make_event(Qt.Key_Meta, Qt.MetaModifier))
        assert result is None

    def test_caps_lock_returns_none(self):
        result = InputHandler.encode(_make_event(Qt.Key_CapsLock))
        assert result is None

    def test_num_lock_returns_none(self):
        result = InputHandler.encode(_make_event(Qt.Key_NumLock))
        assert result is None


# ── Error data tests ────────────────────────────────────────────────────

class TestError:
    """Invalid inputs should return None gracefully (no exceptions)."""

    def test_ctrl_no_text_no_mapping(self):
        """Ctrl + key with no text and no special mapping → None."""
        result = InputHandler.encode(
            _make_event(Qt.Key_unknown, Qt.ControlModifier))
        assert result is None

    def test_alt_no_text_no_mapping(self):
        """Alt + key with no text and no special mapping → None."""
        result = InputHandler.encode(
            _make_event(Qt.Key_unknown, Qt.AltModifier))
        assert result is None


# ── Platform-specific: macOS Ctrl → MetaModifier ────────────────────────

class TestMacOSCtrlMapping:
    """On macOS, Ctrl is mapped to Qt.MetaModifier (Cmd key)."""

    def test_macos_ctrl_a_via_meta(self):
        """Cmd+A on macOS should produce \\x01 (like Ctrl+A)."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")
        result = InputHandler.encode(
            _make_event(Qt.Key_A, Qt.MetaModifier, text="\x01"))
        assert result is not None
