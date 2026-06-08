"""Unit tests for block_chars.draw_block_fill().

Tests cover:
  - Normal data: known block characters → True
  - Boundary data: range edge chars, non-block chars → False
  - Error data: invalid char input
"""

import pytest
from PySide6.QtGui import QColor, QImage, QPainter

from terminal.block_chars import draw_block_fill

# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def painter(qapp) -> QPainter:
    """Create a QPainter backed by a QImage (needed for fillRect calls)."""
    image = QImage(80, 24, QImage.Format_ARGB32)
    image.fill(QColor(0, 0, 0))
    p = QPainter(image)
    yield p
    p.end()


# ── Normal data tests ───────────────────────────────────────────────────

class TestBlockChars:
    """Known block characters should return True (drawn as filled rect)."""

    def test_full_block(self, painter):
        assert draw_block_fill(painter, "\u2588", 0, 0, 10, 20, (255, 0, 0))

    def test_upper_half_block(self, painter):
        assert draw_block_fill(painter, "\u2580", 0, 0, 10, 20, (255, 0, 0))

    def test_lower_half_block(self, painter):
        assert draw_block_fill(painter, "\u2584", 0, 0, 10, 20, (255, 0, 0))

    def test_left_half_block(self, painter):
        assert draw_block_fill(painter, "\u258c", 0, 0, 10, 20, (255, 0, 0))

    def test_right_half_block(self, painter):
        assert draw_block_fill(painter, "\u2590", 0, 0, 10, 20, (255, 0, 0))

    def test_lower_one_eighth_block(self, painter):
        assert draw_block_fill(painter, "\u2581", 0, 0, 10, 20, (255, 0, 0))

    def test_lower_seven_eighth_block(self, painter):
        assert draw_block_fill(painter, "\u2587", 0, 0, 10, 20, (255, 0, 0))

    def test_left_seven_eighth_block(self, painter):
        assert draw_block_fill(painter, "\u2589", 0, 0, 10, 20, (255, 0, 0))

    def test_left_one_eighth_block(self, painter):
        assert draw_block_fill(painter, "\u258f", 0, 0, 10, 20, (255, 0, 0))

    def test_upper_one_eighth_block(self, painter):
        assert draw_block_fill(painter, "\u2594", 0, 0, 10, 20, (255, 0, 0))

    def test_right_one_eighth_block(self, painter):
        assert draw_block_fill(painter, "\u2595", 0, 0, 10, 20, (255, 0, 0))


# ── Boundary data tests ─────────────────────────────────────────────────

class TestBlockCharsBoundary:
    """Edge cases for block character detection."""

    def test_non_block_char_returns_false(self, painter):
        """Regular ASCII letter is not a block char."""
        assert not draw_block_fill(painter, "A", 0, 0, 10, 20, (255, 0, 0))

    def test_space_returns_false(self, painter):
        assert not draw_block_fill(painter, " ", 0, 0, 10, 20, (255, 0, 0))

    def test_shade_block_returns_false(self, painter):
        """Shade characters (U+2591–U+2593) use font rendering."""
        assert not draw_block_fill(painter, "\u2591", 0, 0, 10, 20, (255, 0, 0))

    def test_quadrant_block_returns_false(self, painter):
        """Quadrant characters (U+2596–U+259F) use font rendering."""
        assert not draw_block_fill(painter, "\u2596", 0, 0, 10, 20, (255, 0, 0))

    def test_block_char_zero_dimensions(self, painter):
        """Block char with 0 cell_w should still return True (defensive)."""
        result = draw_block_fill(painter, "\u2588", 0, 0, 0, 20, (255, 0, 0))
        assert result  # still recognized as block char

    def test_range_lower_bound(self, painter):
        """U+2580 (lower bound of block range) is recognized."""
        assert draw_block_fill(painter, "\u2580", 0, 0, 10, 20, (255, 0, 0))

    def test_range_upper_bound(self, painter):
        """U+259F (upper bound) falls through to False (quadrant)."""
        assert not draw_block_fill(painter, "\u259f", 0, 0, 10, 20, (255, 0, 0))


# ── Error data tests ───────────────────────────────────────────────────

class TestBlockCharsError:
    """Invalid inputs should raise TypeError (caller always guards these)."""

    def test_empty_string(self, painter):
        """Empty string — ord() raises TypeError."""
        with pytest.raises(TypeError):
            draw_block_fill(painter, "", 0, 0, 10, 20, (255, 0, 0))

    def test_multi_char_string(self, painter):
        """Multi-char string — ord() raises TypeError (caller ensures len==1)."""
        with pytest.raises(TypeError):
            draw_block_fill(painter, "AB", 0, 0, 10, 20, (255, 0, 0))
