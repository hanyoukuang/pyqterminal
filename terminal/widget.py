from par_term_emu_core_rust import PtyTerminal, CursorStyle, UnderlineStyle, Terminal, MouseEncoding
from PySide6.QtWidgets import QWidget, QApplication, QMenu
from PySide6.QtCore import QTimer, Qt, QRectF, Signal
from PySide6.QtGui import (
    QPainter, QFont, QFontMetrics, QColor,
    QKeyEvent, QPaintEvent, QResizeEvent,
    QWheelEvent, QMouseEvent, QAction,
    QInputMethodEvent, QPainterPath,
)
import sys
import logging

from .input_handler import InputHandler

_log = logging.getLogger(__name__)


_FONT_CANDIDATES = (
    "MesloLGS NF", "JetBrainsMono Nerd Font",
    "FiraCode Nerd Font", "CaskaydiaCove Nerd Font",
    "Hack Nerd Font", "DejaVuSansMono Nerd Font",
    "SF Mono", "JetBrains Mono", "Fira Code",
    "Menlo", "Courier New", "monospace",
)


def _pick_monospace_font(size: int = 13) -> QFont:
    for family in _FONT_CANDIDATES:
        font = QFont(family, size)
        font.setStyleHint(QFont.Monospace)
        font.setHintingPreference(QFont.PreferVerticalHinting)
        fm = QFontMetrics(font)
        if fm.horizontalAdvance("M") > 0:
            return font
    return QFont("monospace", size)


class TerminalWidget(QWidget):
    # Signals — connect to react to terminal events in embedding applications.
    title_changed = Signal(str)    # Shell changed the window title
    process_exited = Signal(int)   # Shell process exited with return code
    bell_rang = Signal()              # Terminal bell (ASCII BEL, \x07)
    selection_copied = Signal(str)    # Selection text copied, host may react
    notification_received = Signal(str, str)  # OSC 9/777 notification (title, message)
    cwd_changed = Signal(str)         # OSC 7 current directory changed
    progress_changed = Signal(int, int)  # OSC 9;4 progress (state, value 0-100)

    DEFAULT_FG = QColor(192, 192, 192)
    DEFAULT_BG = QColor(0, 0, 0)
    SELECTION_BG = QColor(80, 80, 80)

    def __init__(self, parent=None, rows: int = 24, cols: int = 80,
                 display_only: bool = False,
                 font_family: str | None = None,
                 font_size: int = 13):
        super().__init__(parent)

        self._font_family = font_family
        self._font_size = font_size

        if font_family:
            self._font = QFont(font_family, font_size)
            self._font.setStyleHint(QFont.Monospace)
            self._font.setHintingPreference(QFont.PreferVerticalHinting)
        else:
            self._font = _pick_monospace_font(font_size)
        self._fm = QFontMetrics(self._font)
        self._cell_w = int(max(self._fm.horizontalAdvance("M"), 1))
        self._cell_h = int(max(self._fm.height(), 1))

        self._rows = rows
        self._cols = cols
        self._scroll_offset = 0
        self._wheel_accum = 0
        self._unseen_output = False
        self._cursor_visible = True
        self._blink_visible = True
        self._generation = 0
        self._display_only = display_only
        self._active_bg = None
        self._prev_title = ""
        self._prev_clipboard = ""
        self._prev_cwd = ""
        self._prev_progress = (-1, -1)

        self._font_bold = QFont(self._font)
        self._font_bold.setBold(True)
        self._font_italic = QFont(self._font)
        self._font_italic.setItalic(True)
        self._font_bold_italic = QFont(self._font)
        self._font_bold_italic.setBold(True)
        self._font_bold_italic.setItalic(True)

        if display_only:
            self._term = Terminal(self._cols, self._rows, scrollback=10000)
        else:
            self._term = PtyTerminal(self._cols, self._rows, scrollback=10000)
            self._term.set_accept_osc7(True)

        self._mouse_term = Terminal(self._cols, self._rows)

        self._sel_start: tuple[int, int] | None = None
        self._sel_end: tuple[int, int] | None = None
        self._selecting = False
        self._mouse_held = False
        self._last_motion_cell = (-1, -1)
        self._drag_start_pos = None
        self._drag_start_cell = (0, 0)
        self._preedit = ""

        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WA_InputMethodEnabled, True)
        self.setMinimumSize(self._cell_w * 20, self._cell_h * 5)
        self.setMouseTracking(True)

        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._toggle_cursor)
        self._cursor_timer.start(530)

        self._poll_timer: QTimer | None = None
        if not display_only:
            self._poll_timer = QTimer(self)
            self._poll_timer.timeout.connect(self._poll_updates)
            self._poll_timer.start(16)

    def start_shell(self) -> None:
        """Start interactive shell (PtyTerminal mode only)."""
        if self._display_only:
            raise RuntimeError("start_shell() not available in display-only mode")
        try:
            self._term.spawn_shell()
            _log.info("PTY session started")
        except Exception:
            _log.exception("spawn_shell failed")

    def feed(self, data: str) -> None:
        """Feed text/escape sequences for display (display-only mode).

        Use this to pipe terminal output (e.g. from SSH) into the widget
        for rendering without a local PTY.

        Example:
            widget.feed("\\x1b[31mHello\\x1b[0m\\n")
        """
        if not self._display_only:
            raise RuntimeError("feed() only available in display-only mode")
        self._term.process_str(data)
        self._bridge_osc()
        self.update()

    @property
    def rows(self) -> int:
        return self._rows

    @property
    def cols(self) -> int:
        return self._cols

    # ── Polling ──────────────────────────────────────────────────────────

    def _poll_updates(self) -> None:
        try:
            if self._display_only:
                return
            if self._term.has_updates_since(self._generation):
                self._generation = self._term.update_generation()
                if self._scroll_offset == 0:
                    self._unseen_output = False
                    self.update()
                elif not self._unseen_output:
                    self._unseen_output = True
                    self.update()

            try:
                self._term.drain_responses()
            except Exception:
                pass

            self._sync_mouse_term()
            self._bridge_osc()
        except Exception:
            _log.exception("_poll_updates failed")

    def _bridge_osc(self) -> None:
        try:
            title = self._term.title()
            if title and title != self._prev_title:
                self._prev_title = title
                self.title_changed.emit(title)
        except Exception:
            pass

        # OSC 52 clipboard bridge
        try:
            text = self._term.clipboard()
            if text and text != self._prev_clipboard:
                self._prev_clipboard = text
                QApplication.clipboard().setText(text)
        except Exception:
            pass

        # OSC 7 current directory
        try:
            cwd = self._term.current_directory()
            if cwd and cwd != self._prev_cwd:
                self._prev_cwd = cwd
                self.cwd_changed.emit(cwd)
        except Exception:
            pass

        # OSC 9/777 notifications
        try:
            if self._term.has_notifications():
                for title, msg in self._term.drain_notifications():
                    self.notification_received.emit(title or "", msg)
                    self._os_notify(title or "", msg)
        except Exception:
            pass

        # OSC 9;4 progress bar
        try:
            if self._term.has_progress():
                bar = self._term.progress_bar()
                if bar:
                    state = bar.state.value if hasattr(bar.state, 'value') else int(bar.state)
                    val = int(bar.value)
                    if (state, val) != self._prev_progress:
                        self._prev_progress = (state, val)
                        self.progress_changed.emit(state, val)
        except Exception:
            pass

    @staticmethod
    def _os_notify(title: str, message: str) -> None:
        import subprocess
        try:
            if sys.platform == "darwin":
                subprocess.run(
                    ["osascript", "-e",
                     f'display notification "{message}" with title "{title or "Terminal"}"'],
                    capture_output=True, timeout=3)
            elif sys.platform == "linux":
                subprocess.run(
                    ["notify-send", title or "Terminal", message],
                    capture_output=True, timeout=3)
        except Exception:
            pass

    def _sync_mouse_term(self) -> None:
        try:
            mode = self._term.mouse_mode()
            if mode != "off":
                self._mouse_term.process_str(f"\x1b[?1002h")
                self._mouse_term.process_str(f"\x1b[?1006h")
        except Exception:
            pass

    # ── Paint ────────────────────────────────────────────────────────────

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        try:
            painter.setFont(self._font)
            painter.fillRect(self.rect(), self.DEFAULT_BG)

            for display_row in range(self._rows):
                self._draw_row(painter, display_row)

            if self._scroll_offset == 0:
                if self._preedit:
                    self._draw_preedit(painter)
                else:
                    self._draw_cursor(painter)

            if self._unseen_output and self._scroll_offset > 0:
                indicator_w = self._cell_w * 3
                indicator_h = 3
                indicator_x = self._cols * self._cell_w - indicator_w
                indicator_y = self._rows * self._cell_h - indicator_h
                painter.fillRect(indicator_x, indicator_y,
                                 indicator_w, indicator_h,
                                 QColor(255, 200, 0))
        except Exception:
            _log.exception("paintEvent failed")
        finally:
            painter.end()

    def _draw_row(self, painter: QPainter, display_row: int) -> None:
        y = display_row * self._cell_h
        live_row = display_row - self._scroll_offset

        if live_row < 0:
            self._draw_scrollback_row(painter, display_row, y)
        else:
            self._draw_live_row(painter, live_row, y)

    def _draw_scrollback_row(self, painter: QPainter,
                              display_row: int, y: int) -> None:
        sb_len = self._term.scrollback_len()
        sb_idx = sb_len - self._scroll_offset + display_row
        if sb_idx < 0 or sb_idx >= sb_len:
            return
        try:
            cells = self._term.scrollback_line(sb_idx)
        except Exception:
            return
        if not cells:
            return
        self._render_cells(painter, cells, y, display_row, sb_idx)

    def _draw_live_row(self, painter: QPainter,
                        live_row: int, y: int) -> None:
        if live_row >= self._rows:
            return
        try:
            cells = self._term.get_line_cells(live_row)
        except Exception:
            return
        display_row = live_row + self._scroll_offset
        self._render_cells(painter, cells, y, display_row, live_row)

    def _render_cells(self, painter: QPainter, cells: list,
                       y: int, display_row: int,
                       buffer_row: int = -1) -> None:
        cell_data: list[dict] = []
        for col, (char, fg, bg, attrs) in enumerate(cells):
            if col >= self._cols:
                break
            if attrs and attrs.wide_char_spacer:
                continue

            x = col * self._cell_w
            is_wide = attrs and attrs.wide_char
            cell_w = self._cell_w * 2 if is_wide else self._cell_w
            is_space = not char or char.isspace() or char == "\x00"

            is_reverse = attrs and attrs.reverse
            if is_reverse:
                eff_fg = bg if bg else (0, 0, 0)
                eff_bg = fg if fg else (192, 192, 192)
            else:
                eff_fg = fg
                eff_bg = bg

            bg_rgb = eff_bg if eff_bg else (0, 0, 0)
            selected = self._cell_in_selection(display_row, col)

            hyperlink = ""
            if buffer_row >= 0:
                try:
                    hyperlink = self._term.get_hyperlink(col, buffer_row) or ""
                except Exception:
                    pass

            cell_data.append({
                'x': x, 'cell_w': cell_w, 'char': char,
                'eff_fg': eff_fg, 'bg_rgb': bg_rgb,
                'selected': selected, 'attrs': attrs,
                'is_space': is_space, 'hyperlink': hyperlink,
            })

        last_bg = None
        for d in cell_data:
            if d['bg_rgb'] != (0, 0, 0):
                last_bg = d['bg_rgb']
                break

        if last_bg is None and self._active_bg is not None:
            last_bg = self._active_bg
        elif last_bg is None and buffer_row >= 0:
            for next_row in range(buffer_row + 1, min(buffer_row + 8, self._rows)):
                try:
                    for _, _, bg, _ in self._term.get_line_cells(next_row):
                        if bg != (0, 0, 0):
                            last_bg = bg
                            break
                except Exception:
                    continue
                if last_bg is not None:
                    break

        if last_bg is not None and last_bg != (0, 0, 0):
            self._active_bg = last_bg

        if last_bg is not None:
            painter.fillRect(0, y, self._cols * self._cell_w, self._cell_h,
                             QColor(*last_bg))

        for d in cell_data:
            if d['selected']:
                painter.fillRect(d['x'], y, d['cell_w'], self._cell_h,
                                 self.SELECTION_BG)
            elif last_bg is None or d['bg_rgb'] != last_bg:
                painter.fillRect(d['x'], y, d['cell_w'], self._cell_h,
                                 QColor(*d['bg_rgb']))

        for d in cell_data:
            attrs = d['attrs']
            char = d['char']
            x = d['x']
            cell_w = d['cell_w']

            if attrs and attrs.hidden:
                continue
            if d['is_space']:
                continue
            if attrs and attrs.blink and not self._blink_visible:
                continue

            fg_rgb = d['eff_fg'] if d['eff_fg'] else (192, 192, 192)
            if attrs and attrs.dim:
                fg_rgb = tuple(c // 2 for c in fg_rgb)

            is_bold = attrs and attrs.bold
            is_italic = attrs and attrs.italic
            is_underline = attrs and attrs.underline

            if is_bold and is_italic:
                painter.setFont(self._font_bold_italic)
            elif is_bold:
                painter.setFont(self._font_bold)
            elif is_italic:
                painter.setFont(self._font_italic)
            else:
                painter.setFont(self._font)

            painter.save()

            is_block = len(char) == 1 and 0x2580 <= ord(char) <= 0x259F
            if is_block and self._draw_block_fill(painter, char, x, y,
                                                   cell_w, self._cell_h, fg_rgb):
                pass  # drawn as filled rect — seamless, no gaps
            elif is_block:
                painter.setClipRect(x, y, cell_w, self._cell_h)
                self._draw_text_path(painter, char, x, y, fg_rgb)
            else:
                painter.setClipRect(x - 2, y - 2, cell_w + 4, self._cell_h + 4)
                self._draw_text_path(painter, char, x, y, fg_rgb)

            if attrs and attrs.strikethrough:
                mid_y = y + self._cell_h // 2
                painter.drawLine(x, mid_y, x + cell_w, mid_y)

            if is_underline:
                base_y = y + self._fm.ascent() + 2
                ul_style = attrs.underline_style
                self._draw_underline(painter, x, base_y, cell_w, ul_style)

            if d.get('hyperlink'):
                link_y = y + self._fm.ascent() + 2
                painter.setPen(QColor(80, 160, 255))
                painter.drawLine(x, int(link_y), x + cell_w, int(link_y))

            painter.restore()

        painter.setFont(self._font)

    @staticmethod
    def _draw_text_path(painter: QPainter, char: str, x: int, y: int,
                         fg_rgb: tuple) -> None:
        """Draw a single character via QPainterPath for proper glyph counters.

        QPainter.drawText() may fill glyph counters (holes) on some platforms
        when the font's contour winding doesn't match the renderer's expectation.
        QPainterPath.addText() + drawPath() uses the even-odd fill rule,
        preserving counter shapes in Nerd Font icons and other glyphs.
        """
        path = QPainterPath()
        path.addText(x, int(y + painter.fontMetrics().ascent()),
                      painter.font(), char)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*fg_rgb))
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.drawPath(path)

    @staticmethod
    def _draw_block_fill(painter: QPainter, char: str, x: int, y: int,
                          cell_w: int, cell_h: int, fg_rgb: tuple) -> bool:
        """Draw Unicode block element (U+2580–U+259F) as filled rectangle.

        Returns True if drawn, False to fallback to font rendering.
        Draws as filled rect to eliminate sub-pixel gaps between adjacent cells.
        """
        cp = ord(char)
        color = QColor(*fg_rgb)

        if cp == 0x2588:                          # █ FULL BLOCK
            painter.fillRect(x, y, cell_w, cell_h, color)
        elif cp == 0x2580:                        # ▀ UPPER HALF BLOCK
            painter.fillRect(x, y, cell_w, cell_h // 2, color)
        elif cp == 0x2584:                        # ▄ LOWER HALF BLOCK
            half = cell_h // 2
            painter.fillRect(x, y + half, cell_w, cell_h - half, color)
        elif cp == 0x258C:                        # ▌ LEFT HALF BLOCK
            painter.fillRect(x, y, cell_w // 2, cell_h, color)
        elif cp == 0x2590:                        # ▐ RIGHT HALF BLOCK
            half = cell_w // 2
            painter.fillRect(x + half, y, cell_w - half, cell_h, color)
        elif 0x2581 <= cp <= 0x2587:              # ▁-▇ Lower 1/8 … 7/8
            frac = (cp - 0x2580) / 8
            fill_h = max(1, int(cell_h * frac))
            painter.fillRect(x, y + cell_h - fill_h, cell_w, fill_h, color)
        elif 0x2589 <= cp <= 0x258F:              # ▉-▏ Left 7/8 … 1/8
            frac = (0x2590 - cp) / 8
            fill_w = max(1, int(cell_w * frac))
            painter.fillRect(x, y, fill_w, cell_h, color)
        elif cp == 0x2594:                        # ▔ UPPER 1/8 BLOCK
            painter.fillRect(x, y, cell_w, max(1, cell_h // 8), color)
        elif cp == 0x2595:                        # ▕ RIGHT 1/8 BLOCK
            fill_w = max(1, cell_w // 8)
            painter.fillRect(x + cell_w - fill_w, y, fill_w, cell_h, color)
        else:
            return False  # shade / quadrant — use font
        return True

    @staticmethod
    def _draw_underline(painter: QPainter, x: int, base_y: int,
                         cell_w: int, style) -> None:
        """Draw underline with style: Straight, Double, Curly, Dotted, Dashed."""
        if style == UnderlineStyle.Double:
            painter.drawLine(x, base_y - 1, x + cell_w, base_y - 1)
            painter.drawLine(x, base_y + 1, x + cell_w, base_y + 1)
        elif style == UnderlineStyle.Curly:
            # Approximate with short dashes
            pen = painter.pen()
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(x, base_y, x + cell_w, base_y)
            pen.setStyle(Qt.SolidLine)
            painter.setPen(pen)
        elif style == UnderlineStyle.Dotted:
            pen = painter.pen()
            pen.setStyle(Qt.DotLine)
            painter.setPen(pen)
            painter.drawLine(x, base_y, x + cell_w, base_y)
            pen.setStyle(Qt.SolidLine)
            painter.setPen(pen)
        elif style == UnderlineStyle.Dashed:
            pen = painter.pen()
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(x, base_y, x + cell_w, base_y)
            pen.setStyle(Qt.SolidLine)
            painter.setPen(pen)
        else:
            # Straight (default) or None
            painter.drawLine(x, base_y, x + cell_w, base_y)

    def _draw_cursor(self, painter: QPainter) -> None:
        if not self._cursor_visible:
            return
        try:
            if not self._term.cursor_visible():
                return
        except Exception:
            pass
        try:
            cx, cy = self._term.cursor_position()
            style = self._term.cursor_style()
        except Exception:
            return
        if not (0 <= cy < self._rows and 0 <= cx < self._cols):
            return

        x = cx * self._cell_w
        y = cy * self._cell_h

        _UNDERLINE = {CursorStyle.BlinkingUnderline, CursorStyle.SteadyUnderline}
        _BAR = {CursorStyle.BlinkingBar, CursorStyle.SteadyBar}

        if style in _UNDERLINE:
            painter.fillRect(x, y + self._cell_h - 2, self._cell_w, 2,
                             self.DEFAULT_FG)
        elif style in _BAR:
            painter.fillRect(x, y, 2, self._cell_h, self.DEFAULT_FG)
        else:
            painter.fillRect(x, y, self._cell_w, self._cell_h, self.DEFAULT_FG)

    def _draw_preedit(self, painter: QPainter) -> None:
        try:
            cx, cy = self._term.cursor_position()
        except Exception:
            return
        if not (0 <= cy < self._rows and 0 <= cx < self._cols):
            return

        x = cx * self._cell_w
        y = cy * self._cell_h
        preedit_w = len(self._preedit) * self._cell_w

        painter.fillRect(x, y, preedit_w, self._cell_h, self.DEFAULT_BG)

        painter.setFont(self._font)
        painter.setPen(self.DEFAULT_FG)
        painter.drawText(x, int(y + self._fm.ascent()), self._preedit)

        ul_y = y + self._cell_h - 2
        painter.drawLine(x, int(ul_y), x + preedit_w, int(ul_y))

        if self._cursor_visible:
            cx_end = x + preedit_w
            painter.fillRect(cx_end, y, self._cell_w, self._cell_h,
                             self.DEFAULT_FG)

    # ── Selection ────────────────────────────────────────────────────────

    @staticmethod
    def _in_range(val: int, a: int, b: int) -> bool:
        lo, hi = (a, b) if a <= b else (b, a)
        return lo <= val <= hi

    def _cell_in_selection(self, row: int, col: int) -> bool:
        if not self._sel_start or not self._sel_end:
            return False
        r1, c1 = self._sel_start
        r2, c2 = self._sel_end
        if r1 == r2:
            return row == r1 and self._in_range(col, c1, c2)
        if row < min(r1, r2) or row > max(r1, r2):
            return False
        if row == r1:
            return col >= c1 if r1 <= r2 else col <= c1
        if row == r2:
            return col <= c2 if r1 <= r2 else col >= c2
        return True

    def _selected_text(self) -> str:
        if not self._sel_start or not self._sel_end:
            return ""
        r1, c1 = self._sel_start
        r2, c2 = self._sel_end
        if r1 > r2 or (r1 == r2 and c1 > c2):
            r1, c1, r2, c2 = r2, c2, r1, c1

        lines = []
        sb_len = self._term.scrollback_len()
        for r in range(r1, r2 + 1):
            live_row = r - self._scroll_offset
            if live_row < 0:
                sb_idx = sb_len - self._scroll_offset + r
                try:
                    cells = self._term.scrollback_line(sb_idx)
                except Exception:
                    cells = []
            else:
                if live_row >= self._rows:
                    continue
                try:
                    cells = self._term.get_line_cells(live_row)
                except Exception:
                    cells = []

            if not cells:
                continue

            sc = c1 if r == r1 else 0
            ec = c2 if r == r2 else self._cols - 1

            line_str = ""
            for col, (char, fg, bg, attrs) in enumerate(cells):
                if col > ec:
                    break
                if col >= sc:
                    if attrs and attrs.wide_char_spacer:
                        continue
                    line_str += char if char else " "

            lines.append(line_str.rstrip())

        return "\n".join(lines)

    def _copy_selection(self) -> None:
        text = self._selected_text()
        if text:
            QApplication.clipboard().setText(text)

    def _clear_selection(self) -> None:
        self._sel_start = None
        self._sel_end = None
        self.update()

    def clear_selection(self) -> None:
        """Clear the selection highlight. Callable by host applications."""
        self._clear_selection()

    def _hyperlink_at(self, col: int, row: int) -> str:
        live_row = row - self._scroll_offset
        try:
            if live_row < 0:
                sb_idx = self._term.scrollback_len() + live_row
                return ""  # scrollback hyperlinks not yet supported
            elif live_row < self._rows:
                return self._term.get_hyperlink(col, live_row) or ""
        except Exception:
            pass
        return ""

    # ── Mouse events ─────────────────────────────────────────────────────

    def _mouse_tracking_active(self) -> bool:
        """True when the terminal app has requested mouse tracking."""
        if self._display_only:
            return False
        try:
            return self._term.mouse_mode() != "off"
        except Exception:
            return False

    def _send_mouse_event(self, event: QMouseEvent, pressed: bool,
                            motion: bool = False) -> None:
        if self._display_only:
            return
        col = int(event.position().x() // self._cell_w)
        row = int(event.position().y() // self._cell_h)
        btn = event.button()
        if btn == Qt.LeftButton:
            code = 0
        elif btn == Qt.MiddleButton:
            code = 1
        elif btn == Qt.RightButton:
            code = 2
        else:
            code = 0

        modifiers = event.modifiers()
        if modifiers & Qt.ShiftModifier:
            code += 4
        if modifiers & (Qt.AltModifier | Qt.MetaModifier):
            code += 8
        if modifiers & Qt.ControlModifier:
            code += 16

        is_sgr = self._mouse_term.mouse_encoding() == MouseEncoding.Sgr
        if not motion:
            seq = self._mouse_term.simulate_mouse_event(code & 3, col, row, pressed)
            if seq:
                self._term.write(seq)
        elif is_sgr:
            if pressed:
                code += 32
            seq = f"\x1b[<{code};{col + 1};{row + 1}{'M' if pressed else 'm'}".encode()
            self._term.write(seq)
        else:
            col = min(col, 222)
            row = min(row, 222)
            code += 32
            seq = b"\x1b[M" + bytes([code + 32]) + bytes([col + 32]) + bytes([row + 32])
            self._term.write(seq)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        try:
            self._mouse_press_impl(event)
        except Exception:
            _log.exception("mousePressEvent failed")

    def _mouse_press_impl(self, event: QMouseEvent) -> None:
        col = int(event.position().x() // self._cell_w)
        row = int(event.position().y() // self._cell_h)
        if self._mouse_tracking_active() and not (event.modifiers() & Qt.ShiftModifier):
            self._send_mouse_event(event, True)
            self._mouse_held = True
            self._last_motion_cell = (col, row)
            return

        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ControlModifier):
            link = self._hyperlink_at(col, row)
            if link:
                import webbrowser
                webbrowser.open(link)
                return

        self._mouse_held = True
        self._last_motion_cell = (col, row)

        if event.button() == Qt.LeftButton:
            self._clear_selection()
            self._drag_start_pos = event.position()
            self._drag_start_cell = (row, col)
            self._selecting = False
            self.setCursor(Qt.IBeamCursor)
        elif event.button() == Qt.MiddleButton:
            if not self._display_only:
                text = QApplication.clipboard().text()
                if text:
                    self._term.write_str(text)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        col = max(0, min(self._cols - 1, int(event.position().x() // self._cell_w)))
        row = max(0, min(self._rows - 1, int(event.position().y() // self._cell_h)))
        cell_changed = (col, row) != self._last_motion_cell

        if not self._selecting and self._mouse_held and self._drag_start_pos:
            dx = event.position().x() - self._drag_start_pos.x()
            dy = event.position().y() - self._drag_start_pos.y()
            if dx * dx + dy * dy >= 1:  # minimal drag threshold
                self._selecting = True
                self._sel_start = self._drag_start_cell
                self._sel_end = self._drag_start_cell

        if self._selecting:
            self._sel_end = (row, col)
            self.update()

        if self._mouse_tracking_active() and self._mouse_held and cell_changed:
            self._send_mouse_event(event, True, motion=True)

        if cell_changed:
            self._last_motion_cell = (col, row)

        if not self._selecting and not self._mouse_tracking_active():
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        try:
            self._mouse_release_impl(event)
        except Exception:
            _log.exception("mouseReleaseEvent failed")

    def _mouse_release_impl(self, event: QMouseEvent) -> None:
        self._mouse_held = False
        self._drag_start_pos = None

        if self._mouse_tracking_active():
            self._send_mouse_event(event, False)
        if event.button() == Qt.LeftButton and self._selecting:
            self._selecting = False
            self.setCursor(Qt.ArrowCursor)
            text = self._selected_text()
            if text:
                QApplication.clipboard().setText(text)
                self.selection_copied.emit(text)
            else:
                self._clear_selection()
        else:
            super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)

        copy_action = QAction("Copy", menu)
        copy_action.setShortcut("Ctrl+Shift+C")
        copy_action.triggered.connect(self._copy_selection)
        copy_action.setEnabled(bool(self._sel_start))
        menu.addAction(copy_action)

        paste_action = QAction("Paste", menu)
        paste_action.setShortcut("Ctrl+Shift+V")
        paste_action.triggered.connect(self._paste_clipboard)
        menu.addAction(paste_action)

        menu.addSeparator()

        zoom_in = QAction("Zoom In", menu)
        zoom_in.setShortcut("Ctrl++")
        zoom_in.triggered.connect(lambda: self._change_font_size(1))
        menu.addAction(zoom_in)

        zoom_out = QAction("Zoom Out", menu)
        zoom_out.setShortcut("Ctrl+-")
        zoom_out.triggered.connect(lambda: self._change_font_size(-1))
        menu.addAction(zoom_out)

        zoom_reset = QAction("Reset Zoom", menu)
        zoom_reset.setShortcut("Ctrl+0")
        zoom_reset.triggered.connect(lambda: self._change_font_size(
            13 - self._font.pointSize()))
        menu.addAction(zoom_reset)

        menu.exec(event.globalPos())

    def _paste_clipboard(self) -> None:
        if self._display_only:
            return
        text = QApplication.clipboard().text()
        if text:
            self._paste_text(text)

    def _paste_text(self, text: str) -> None:
        try:
            if self._term.bracketed_paste():
                self._term.write_str("\x1b[200~" + text + "\x1b[201~")
            else:
                self._term.write_str(text)
        except Exception:
            self._term.write_str(text)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._display_only:
            return

        self._wheel_accum += event.angleDelta().y()
        threshold = self._cell_h
        lines = int(self._wheel_accum // threshold)
        if lines == 0:
            return
        self._wheel_accum %= threshold

        if self._term.mouse_mode() != "off":
            self._send_mouse_wheel(event, lines)
        else:
            max_scroll = max(self._term.scrollback_len(), self._rows * 100)
            self._scroll_offset = max(0, min(max_scroll,
                                      self._scroll_offset - lines))
            self.update()

    def _send_mouse_wheel(self, event: QWheelEvent, lines: int) -> None:
        col = int(event.position().x() // self._cell_w)
        row = int(event.position().y() // self._cell_h)
        button = 64 if lines > 0 else 65
        col = min(col, 222)
        row = min(row, 222)
        for _ in range(abs(lines)):
            seq = b"\x1b[M" + bytes([button + 32]) + bytes([col + 32]) + bytes([row + 32])
            self._term.write(seq)

    # ── Keyboard ─────────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:
        try:
            self._key_press_impl(event)
        except Exception:
            _log.exception("keyPressEvent failed")

    def _key_press_impl(self, event: QKeyEvent) -> None:
        key = event.key()
        mods = event.modifiers()

        zoom_mod = bool(mods & Qt.ControlModifier)
        if sys.platform != "darwin":
            zoom_mod = zoom_mod and bool(mods & Qt.ShiftModifier)
        if zoom_mod and key in (Qt.Key_Plus, Qt.Key_Equal, Qt.Key_Minus):
            delta = 1 if key != Qt.Key_Minus else -1
            self._change_font_size(delta)
            return
        if zoom_mod and key == Qt.Key_0:
            self._change_font_size(13 - self._font.pointSize())
            return
        if key == Qt.Key_PageUp and mods & Qt.ShiftModifier:
            max_scroll = max(self._term.scrollback_len(), self._rows * 100)
            self._scroll_offset = min(max_scroll,
                                      self._scroll_offset + self._rows // 2)
            self.update()
            return
        if key == Qt.Key_PageDown and mods & Qt.ShiftModifier:
            self._scroll_offset = max(0,
                                      self._scroll_offset - self._rows // 2)
            self.update()
            return

        # Copy: Cmd+C (macOS) or Ctrl+Shift+C
        copy_key = key == Qt.Key_C
        copy_mod = bool(mods & Qt.ControlModifier)
        if sys.platform == "darwin":
            is_copy = copy_key and copy_mod and not (mods & Qt.ShiftModifier)
        else:
            is_copy = copy_key and copy_mod and bool(mods & Qt.ShiftModifier)
        if is_copy:
            self._copy_selection()
            return

        # Paste: Cmd+V (macOS) or Ctrl+Shift+V
        paste_key = key == Qt.Key_V
        paste_mod = bool(mods & Qt.ControlModifier)
        if sys.platform == "darwin":
            is_paste = paste_key and paste_mod and not (mods & Qt.ShiftModifier)
        else:
            is_paste = paste_key and paste_mod and bool(mods & Qt.ShiftModifier)
        if is_paste:
            self._clear_selection()
            if not self._display_only:
                text = QApplication.clipboard().text()
                if text:
                    self._paste_text(text)
            return

        if not self._display_only:
            data = InputHandler.encode(event)
            if data:
                self._term.write(data)

    def inputMethodEvent(self, event: QInputMethodEvent) -> None:
        commit = event.commitString()
        if commit:
            self._term.write_str(commit)
        self._preedit = event.preeditString()
        self.update()

    def inputMethodQuery(self, query: Qt.InputMethodQuery):
        if query == Qt.ImCursorRectangle:
            try:
                cx, cy = self._term.cursor_position()
            except Exception:
                return QRectF()
            x = cx * self._cell_w
            y = cy * self._cell_h
            return QRectF(x, y, self._cell_w, self._cell_h)
        return None

    # ── Resize ────────────────────────────────────────────────────────────

    def resizeEvent(self, event: QResizeEvent) -> None:
        new_cols = max(1, self.width() // self._cell_w)
        new_rows = max(1, self.height() // self._cell_h)

        if new_cols != self._cols or new_rows != self._rows:
            self._cols = new_cols
            self._rows = new_rows
            self._term.resize(self._cols, self._rows)
            self._mouse_term.resize(self._cols, self._rows)

        self.update()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _toggle_cursor(self) -> None:
        self._cursor_visible = not self._cursor_visible
        self._blink_visible = not self._blink_visible
        self.update()

    def _change_font_size(self, delta: int) -> None:
        size = max(6, min(32, self._font.pointSize() + delta))
        self._font = _pick_monospace_font(size)
        self._fm = QFontMetrics(self._font)
        self._cell_w = int(max(self._fm.horizontalAdvance("M"), 1))
        self._cell_h = int(max(self._fm.height(), 1))

        self._font_bold = QFont(self._font)
        self._font_bold.setBold(True)
        self._font_italic = QFont(self._font)
        self._font_italic.setItalic(True)
        self._font_bold_italic = QFont(self._font)
        self._font_bold_italic.setBold(True)
        self._font_bold_italic.setItalic(True)

        new_cols = max(1, self.width() // self._cell_w)
        new_rows = max(1, self.height() // self._cell_h)
        self._cols = new_cols
        self._rows = new_rows
        self._term.resize(self._cols, self._rows)
        self.update()
