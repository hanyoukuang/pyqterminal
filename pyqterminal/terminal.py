from .cyvterm import TerminalScreen
from PySide6.QtWidgets import QWidget, QApplication, QScrollBar
from PySide6.QtGui import (
    QPainter,
    QFont,
    QFontMetrics,
    QFontMetricsF,
    QColor,
    QFontDatabase,
    QKeySequence,
    QGuiApplication,
    QClipboard,
    QInputMethodEvent,
)
from PySide6.QtCore import Qt, QRect, QRectF, QTimer, Signal, QPointF


class PyqTerminal(QWidget):
    resized = Signal(int, int)  # rows, cols
    keyPressed = Signal(str)  # For sending input to PTY

    def __init__(self, parent=None, rows=24, cols=80, font_family=None, font_size=14):
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.padding = 8
        self.scroll_offset = 0

        self.setFocusPolicy(Qt.WheelFocus)  # Allow widget to receive keyboard events
        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)

        # Setup Cyvterm
        self.vt = TerminalScreen(self.rows, self.cols, 10000)

        # Setup Font
        if font_family is None:
            self.terminal_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
            self.terminal_font.setPointSize(font_size)
        else:
            self.terminal_font = QFont(font_family, font_size)
        self.terminal_font.setStyleHint(QFont.Monospace)
        self.terminal_font.setFixedPitch(True)
        self.terminal_font.setKerning(False)
        self.setFont(self.terminal_font)

        self._color_cache = {}
        self._font_cache = {}
        self._update_metrics()

        # Basic 16 colors mapping
        self.color_map = {
            "black": QColor(0, 0, 0),
            "red": QColor(205, 0, 0),
            "green": QColor(0, 205, 0),
            "brown": QColor(205, 205, 0),
            "blue": QColor(0, 0, 238),
            "magenta": QColor(205, 0, 205),
            "cyan": QColor(0, 205, 205),
            "white": QColor(229, 229, 229),
        }
        self.default_bg = QColor(0, 0, 0)
        self.default_fg = QColor(229, 229, 229)

        # Selection state
        self.selection_start = None  # (row, col)
        self.selection_end = None  # (row, col)
        self._last_mouse_grid = None
        self._scroll_accum_y = 0

        self._raw_buffer = bytearray()  # For OSC 52 interception

        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WA_InputMethodEnabled, True)  # 允许操作系统输入法 (IME)
        self.setMouseTracking(True)  # Track mouse for TUI motion events

        # Scrollbar
        self.scrollbar = QScrollBar(Qt.Vertical, self)
        self.scrollbar.valueChanged.connect(self._on_scroll_bar)
        self.scrollbar.hide()

        # Render throttler (60fps)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(16)
        self._refresh_timer.timeout.connect(self._do_refresh)
        self._refresh_timer.start()

        self._scrollbar_throttle = 0

    def _update_metrics(self):
        self._font_cache.clear()
        self.metrics = QFontMetricsF(self.terminal_font)
        self.char_width = self.metrics.horizontalAdvance("W")
        self.char_height = self.metrics.height()
        self.ascent = self.metrics.ascent()
        self.setMinimumSize(
            int(self.cols * self.char_width + 2 * self.padding),
            int(self.rows * self.char_height + 2 * self.padding),
        )

    def write(self, data: bytes):
        if isinstance(data, str):
            data = data.encode('utf-8')
        self._raw_buffer.extend(data)

        while True:
            idx = self._raw_buffer.find(b"\x1b]52;")
            if idx == -1:
                safe_len = len(self._raw_buffer)
                for i in range(1, 7):
                    if self._raw_buffer.endswith(b"\x1b]52;"[:i]):
                        safe_len = len(self._raw_buffer) - i
                        break

                if safe_len > 0:
                    self.vt.feed(bytes(self._raw_buffer[:safe_len]))
                    del self._raw_buffer[:safe_len]
                break
            else:
                if idx > 0:
                    self.vt.feed(bytes(self._raw_buffer[:idx]))
                    del self._raw_buffer[:idx]

                term_idx = self._raw_buffer.find(b"\x07")
                term_idx2 = self._raw_buffer.find(b"\x1b\\")

                if term_idx == -1 and term_idx2 == -1:
                    break

                if term_idx != -1 and term_idx2 != -1:
                    end_idx = min(term_idx, term_idx2)
                    term_len = 1 if end_idx == term_idx else 2
                elif term_idx != -1:
                    end_idx = term_idx
                    term_len = 1
                else:
                    end_idx = term_idx2
                    term_len = 2

                payload = bytes(self._raw_buffer[6:end_idx])
                parts = payload.split(b";", 1)
                if len(parts) == 2:
                    try:
                        import base64

                        b64_data = parts[1]
                        b64_data += b"=" * ((4 - len(b64_data) % 4) % 4)
                        decoded_text = base64.b64decode(b64_data).decode("utf-8")
                        clipboard = QGuiApplication.clipboard()
                        clipboard.setText(decoded_text)
                    except Exception:
                        pass

                # Remove the handled sequence
                del self._raw_buffer[: end_idx + term_len]

        out = self.vt.read_output()
        if out:
            self.keyPressed.emit(out.decode('utf-8', 'ignore'))

    def _do_refresh(self):
        if self.vt.dirty_rows:
            scrolled = False
            if self.scroll_offset > 0:
                self.scroll_offset = 0
                scrolled = True
            
            if scrolled:
                self.update()
            else:
                for r in self.vt.dirty_rows:
                    top = int(self.padding + r * self.char_height)
                    bottom = int(self.padding + (r + 1) * self.char_height)
                    self.update(0, top, self.width(), bottom - top)
            
            self.vt.dirty_rows.clear()
        
        self._scrollbar_throttle += 1
        if self._scrollbar_throttle >= 15: # roughly 4 fps for scrollbar updates
            self._update_scrollbar()
            self._scrollbar_throttle = 0

    def _update_scrollbar(self):
        total = self.vt.history_len()
        if total == 0:
            if not self.scrollbar.isHidden():
                self.scrollbar.hide()
            return
        if self.scrollbar.isHidden():
            self.scrollbar.show()
        
        # Only update if values actually changed to prevent expensive Qt layout reflows
        if (self.scrollbar.maximum() != total or 
            self.scrollbar.pageStep() != self.rows or 
            self.scrollbar.value() != total - self.scroll_offset):
            
            self.scrollbar.blockSignals(True)
            if self.scrollbar.maximum() != total:
                self.scrollbar.setMaximum(total)
            if self.scrollbar.pageStep() != self.rows:
                self.scrollbar.setPageStep(self.rows)
            if self.scrollbar.value() != total - self.scroll_offset:
                self.scrollbar.setValue(total - self.scroll_offset)
            self.scrollbar.blockSignals(False)

    def _on_scroll_bar(self, val):
        total = self.vt.history_len()
        self.scroll_offset = total - val
        self.update()

    def _scroll_history(self, delta):
        total = self.vt.history_len()
        if total == 0:
            return
        self.scroll_offset = max(0, min(total, self.scroll_offset + delta))
        self.update()
        self.scrollbar.blockSignals(True)
        self.scrollbar.setValue(total - self.scroll_offset)
        self.scrollbar.blockSignals(False)
        self.update()

    def clear(self):
        self.vt.reset()
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scrollbar.setGeometry(self.width() - 12, 0, 12, self.height())
        self._recalculate_size()
        QGuiApplication.inputMethod().update(Qt.InputMethodQuery.ImCursorRectangle)

    def moveEvent(self, event):
        super().moveEvent(event)
        QGuiApplication.inputMethod().update(Qt.InputMethodQuery.ImCursorRectangle)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        QGuiApplication.inputMethod().update(Qt.InputMethodQuery.ImCursorRectangle)

    def _recalculate_size(self):
        if self.char_width == 0 or self.char_height == 0:
            return
            
        new_cols = int((self.width() - 2 * self.padding) // self.char_width)
        new_rows = int((self.height() - 2 * self.padding) // self.char_height)
        
        if new_cols != self.cols or new_rows != self.rows:
            new_cols = max(1, new_cols)
            new_rows = max(1, new_rows)
            
            self.cols = new_cols
            self.rows = new_rows
            self.vt.resize(self.rows, self.cols)
            self.resized.emit(self.rows, self.cols)

    def set_font_size(self, size: int):
        size = max(6, min(72, size))
        if self.terminal_font.pointSize() == size:
            return
        self.terminal_font.setPointSize(size)
        self.setFont(self.terminal_font)
        self._update_metrics()
        self._recalculate_size()
        self.update()

    def _get_vterm_modifiers(self, event):
        import sys
        mods = 0
        qt_mods = event.modifiers()
        if qt_mods & Qt.ShiftModifier: mods |= 1
        if qt_mods & Qt.AltModifier: mods |= 2
        
        if sys.platform == "darwin":
            if qt_mods & Qt.MetaModifier: mods |= 4
        else:
            if qt_mods & Qt.ControlModifier: mods |= 4
        return mods

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.set_font_size(self.terminal_font.pointSize() + 1)
            elif delta < 0:
                self.set_font_size(self.terminal_font.pointSize() - 1)
            event.accept()
            return

        delta = event.angleDelta().y()
        if delta == 0:
            event.accept()
            return

        row, col = self._mouse_to_grid(event.position())
        mods = self._get_vterm_modifiers(event)

        self._scroll_accum_y += delta
        step = 60
        
        sent_to_tui = False
        original_accum = self._scroll_accum_y

        while self._scroll_accum_y >= step:
            self._scroll_accum_y -= step
            self.vt.mouse_button(4, 1, mods)
            out = self.vt.read_output()
            if out:
                self.keyPressed.emit(out.decode('utf-8'))
                sent_to_tui = True
                
        while self._scroll_accum_y <= -step:
            self._scroll_accum_y += step
            self.vt.mouse_button(5, 1, mods)
            out = self.vt.read_output()
            if out:
                self.keyPressed.emit(out.decode('utf-8'))
                sent_to_tui = True

        if sent_to_tui:
            event.accept()
            return

        self._scroll_accum_y = original_accum
        step = 30
        while self._scroll_accum_y >= step:
            self._scroll_accum_y -= step
            self._scroll_history(1)
        while self._scroll_accum_y <= -step:
            self._scroll_accum_y += step
            self._scroll_history(-1)
        event.accept()

    # --- Mouse and Selection ---
    def _mouse_to_grid(self, pos):
        col = int((pos.x() - self.padding) // self.char_width)
        row = int((pos.y() - self.padding) // self.char_height)
        return max(0, min(self.rows - 1, row)), max(0, min(self.cols - 1, col))

    def _send_mouse_event(self, event, is_press=False, is_release=False, is_move=False):
        if event.modifiers() & Qt.ShiftModifier:
            return False

        row, col = self._mouse_to_grid(event.position())
        mods = self._get_vterm_modifiers(event)

        button = 0
        if is_press or is_release:
            if event.button() == Qt.LeftButton: button = 1
            elif event.button() == Qt.MiddleButton: button = 2
            elif event.button() == Qt.RightButton: button = 3
        else:
            if event.buttons() & Qt.LeftButton: button = 1
            elif event.buttons() & Qt.MiddleButton: button = 2
            elif event.buttons() & Qt.RightButton: button = 3

        if is_move:
            self.vt.mouse_move(row, col, mods)
        elif is_press:
            self.vt.mouse_button(button, 1, mods)
        elif is_release:
            self.vt.mouse_button(button, 0, mods)

        out = self.vt.read_output()
        if out:
            self.keyPressed.emit(out.decode('utf-8'))
            return True
            
        return False

    def mousePressEvent(self, event):
        self._last_mouse_grid = self._mouse_to_grid(event.position())
        if self._send_mouse_event(event, is_press=True):
            return

        if event.button() == Qt.LeftButton:
            self._mouse_press_pos = event.position()
            self._has_dragged = False
            self.selection_start = self._mouse_to_grid(event.position())
            self.selection_end = None
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._last_mouse_grid = self._mouse_to_grid(event.position())
        if self._send_mouse_event(event, is_release=True):
            return

        # Copy automatically on select release
        if getattr(self, "_has_dragged", False) and self.selection_start and self.selection_end:
            self.copy_selection(clear=False)
        else:
            self.selection_start = None
            self.selection_end = None
            self.update()

        self._has_dragged = False
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        grid_pos = self._mouse_to_grid(event.position())
        
        # TUI mouse tracking throttle
        if getattr(self, "_last_mouse_grid", None) == grid_pos:
            tui_throttled = True
        else:
            tui_throttled = False

        if self._send_mouse_event(event, is_move=True):
            # If TUI handled it, we only update last_mouse_grid to prevent spamming
            if not tui_throttled:
                self._last_mouse_grid = grid_pos
            return

        self._last_mouse_grid = grid_pos

        if event.buttons() & Qt.LeftButton:
            if hasattr(self, "_mouse_press_pos"):
                diff = event.position() - self._mouse_press_pos
                if diff.manhattanLength() >= 3:
                    self._has_dragged = True
                    self.selection_end = grid_pos
                    self.update()
                    
        super().mouseMoveEvent(event)

    def _get_selection_range(self):
        if not self.selection_start or not self.selection_end:
            return None
        r1, c1 = self.selection_start
        r2, c2 = self.selection_end
        if (r1, c1) > (r2, c2):
            r1, c1, r2, c2 = r2, c2, r1, c1
        return (r1, c1), (r2, c2)

    def _is_selected(self, row, col, sel_range):
        if not sel_range:
            return False
        (r1, c1), (r2, c2) = sel_range
        if r1 < row < r2:
            return True
        if row == r1 == r2:
            return c1 <= col <= c2
        if row == r1:
            return col >= c1
        if row == r2:
            return col <= c2
        return False

    def copy_selection(self, clear=True):
        sel_range = self._get_selection_range()
        if not sel_range:
            return
        (r1, c1), (r2, c2) = sel_range
        lines = []
        N = self.vt.history_len()

        for r in range(r1, r2 + 1):
            L = N - self.scroll_offset + r
            if L < 0:
                continue  # Out of bounds
            if L < N:
                line = self.vt.get_history_line(L)
            elif L - N < self.rows:
                line = [self.vt.get_cell(L - N, c) for c in range(self.cols)]
            else:
                continue  # Out of bounds

            start_c = c1 if r == r1 else 0
            end_c = c2 if r == r2 else self.cols - 1

            text = ""
            for c in range(start_c, end_c + 1):
                cell = line[c]
                if cell and cell['data'] != "":  # Ignore double cell empty placeholders
                    text += cell['data']
            lines.append(text.rstrip())

        QApplication.clipboard().setText("\n".join(lines))

        if clear:
            self.selection_start = None
            self.selection_end = None
            self.update()

    def paste_clipboard(self):
        text = QApplication.clipboard().text()
        if text:
            # Send pasted text to the PTY
            self.keyPressed.emit(text)

    def inputMethodEvent(self, event):
        """捕获中文等输入法的上屏内容"""
        commit_str = event.commitString()
        if commit_str:
            self.keyPressed.emit(commit_str)
        event.accept()

    def inputMethodQuery(self, query):
        """让输入法候选框精确跟随光标位置"""
        if query == Qt.InputMethodQuery.ImCursorRectangle:
            visual_y = self.vt.cursor_y + self.scroll_offset
            return QRect(
                self.padding + self.vt.cursor_x * self.char_width,
                self.padding + visual_y * self.char_height,
                self.char_width,
                self.char_height,
            )
        elif query == Qt.InputMethodQuery.ImFont:
            return self.terminal_font
        elif query == Qt.InputMethodQuery.ImCursorPosition:
            return 0
        return super().inputMethodQuery(query)

    def keyPressEvent(self, event):
        import sys
        if event.matches(QKeySequence.Copy):
            if sys.platform != "darwin" and not self._get_selection_range():
                # On Windows/Linux, Ctrl+C is Copy. If no text is selected, do not copy, send SIGINT!
                pass
            else:
                self.copy_selection()
                return
        if event.matches(QKeySequence.Paste):
            self.paste_clipboard()
            return

        import sys
        qt_key = event.key()
        vterm_key = 0
        
        if sys.platform == "darwin":
            physical_cmd = bool(event.modifiers() & Qt.ControlModifier)
        else:
            physical_cmd = False
            
        if physical_cmd:
            return  # Ignore unhandled Command shortcuts
        
        if qt_key in (Qt.Key_Return, Qt.Key_Enter): vterm_key = 1
        elif qt_key == Qt.Key_Tab: vterm_key = 2
        elif qt_key == Qt.Key_Backspace: vterm_key = 3
        elif qt_key == Qt.Key_Escape: vterm_key = 4
        elif qt_key == Qt.Key_Up: vterm_key = 5
        elif qt_key == Qt.Key_Down: vterm_key = 6
        elif qt_key == Qt.Key_Left: vterm_key = 7
        elif qt_key == Qt.Key_Right: vterm_key = 8
        elif qt_key == Qt.Key_Insert: vterm_key = 9
        elif qt_key == Qt.Key_Delete: vterm_key = 10
        elif qt_key == Qt.Key_Home: vterm_key = 11
        elif qt_key == Qt.Key_End: vterm_key = 12
        elif qt_key == Qt.Key_PageUp: vterm_key = 13
        elif qt_key == Qt.Key_PageDown: vterm_key = 14
        
        mods = self._get_vterm_modifiers(event)
        
        if vterm_key:
            self.vt.keyboard_key(vterm_key, mods)
        elif (mods & 4) and Qt.Key_A <= qt_key <= Qt.Key_Z:
            char_code = qt_key
            if not (mods & 1):
                char_code += 32  # lowercase
            self.vt.keyboard_unichar(char_code, mods)
        elif (mods & 4) and qt_key in (Qt.Key_BracketLeft, Qt.Key_Backslash, Qt.Key_BracketRight, Qt.Key_AsciiCircum, Qt.Key_Underscore, Qt.Key_Space):
            self.vt.keyboard_unichar(qt_key, mods)
        else:
            text = event.text()
            if text:
                for char in text:
                    # In case Qt gives us raw control characters when we expect normal chars
                    if ord(char) < 32 and not (mods & 4):
                        self.keyPressed.emit(char)
                    else:
                        self.vt.keyboard_unichar(ord(char), mods)
            else:
                super().keyPressEvent(event)
                return
                
        out = self.vt.read_output()
        if out:
            self.keyPressed.emit(out.decode('utf-8'))

    # --- Colors & Rendering ---
    def _get_color(self, vterm_color, is_bg=False):
        key = (vterm_color, is_bg)
        if key in self._color_cache:
            return self._color_cache[key]

        if vterm_color == "default_fg": res = self.default_fg
        elif vterm_color == "default_bg": res = self.default_bg
        elif vterm_color.startswith("#"):
            try: res = QColor(vterm_color)
            except: res = self.default_bg if is_bg else self.default_fg
        elif vterm_color.startswith("index:"):
            idx = int(vterm_color.split(":")[1])
            if 0 <= idx < 8:
                palette = [QColor(0,0,0), QColor(205,0,0), QColor(0,205,0), QColor(205,205,0),
                           QColor(0,0,238), QColor(205,0,205), QColor(0,205,205), QColor(229,229,229)]
                res = palette[idx]
            elif 8 <= idx < 16:
                palette = [QColor(127,127,127), QColor(255,0,0), QColor(0,255,0), QColor(255,255,0),
                           QColor(92,92,255), QColor(255,0,255), QColor(0,255,255), QColor(255,255,255)]
                res = palette[idx - 8]
            else:
                res = self.default_bg if is_bg else self.default_fg
        else:
            res = self.default_bg if is_bg else self.default_fg

        self._color_cache[key] = res
        return res

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(self.terminal_font)

        clip_rect = event.rect()
        painter.fillRect(clip_rect, self.default_bg)
        sel_range = self._get_selection_range()

        # Calculate dirty rows based on clipping rect
        min_y = int(max(0, (clip_rect.top() - self.padding) // self.char_height))
        max_y = int(min(
            self.rows - 1,
            (clip_rect.bottom() - self.padding + self.char_height - 1)
            // self.char_height,
        ))

        N = self.vt.history_len()

        # Pass 1: Draw all backgrounds (Batched!)
        for y in range(min_y, max_y + 1):
            L = N - self.scroll_offset + y
            if L < N:
                line = self.vt.get_history_line(L)
            else:
                line = [self.vt.get_cell(L - N, c) for c in range(self.cols)]

            start_x = 0
            current_bg = None
            skip_next = False

            for x in range(self.cols):
                if skip_next:
                    skip_next = False
                    continue
                    
                char = line[x]
                if not char: continue
                bg_color = self._get_color(char['bg'], is_bg=True)
                if char['reverse']:
                    bg_color = self._get_color(char['fg'], is_bg=False)
                if self._is_selected(y, x, sel_range):
                    fg_temp = self._get_color(char['fg'], is_bg=False)
                    if char['reverse']:
                        fg_temp = self._get_color(char['bg'], is_bg=True)
                    bg_color = fg_temp

                if bg_color != current_bg:
                    if current_bg is not None and current_bg != self.default_bg:
                        top = int(self.padding + y * self.char_height)
                        bottom = int(self.padding + (y + 1) * self.char_height)
                        left = int(self.padding + start_x * self.char_width)
                        right = int(self.padding + x * self.char_width)
                        painter.fillRect(
                            QRect(left, top, right - left, bottom - top),
                            current_bg,
                        )
                    start_x = x
                    current_bg = bg_color
                    
                if char['width'] == 2:
                    skip_next = True

            if current_bg is not None and current_bg != self.default_bg:
                top = int(self.padding + y * self.char_height)
                bottom = int(self.padding + (y + 1) * self.char_height)
                left = int(self.padding + start_x * self.char_width)
                right = int(self.padding + self.cols * self.char_width)
                painter.fillRect(
                    QRect(left, top, right - left, bottom - top),
                    current_bg,
                )

        # Pass 2: Draw all foreground text
        last_pen_color = None
        last_font_key = None

        for y in range(min_y, max_y + 1):
            L = N - self.scroll_offset + y
            if L < N:
                line = self.vt.get_history_line(L)
            else:
                line = [self.vt.get_cell(L - N, c) for c in range(self.cols)]

            x = 0
            while x < self.cols:
                char = line[x]
                if not char or char['data'] in ("", None):
                    x += 1
                    continue

                data = char['data']
                top = int(self.padding + y * self.char_height)
                bottom = int(self.padding + (y + 1) * self.char_height)
                left = int(self.padding + x * self.char_width)
                right = int(self.padding + (x + 1) * self.char_width)
                rect = QRectF(left, top, right - left, bottom - top)

                fg_color = self._get_color(char['fg'], is_bg=False)
                if char['reverse']:
                    fg_color = self._get_color(char['bg'], is_bg=True)
                is_sel = self._is_selected(y, x, sel_range)
                if is_sel:
                    bg_temp = self._get_color(char['bg'], is_bg=True)
                    if char['reverse']:
                        bg_temp = self._get_color(char['fg'], is_bg=False)
                    fg_color = bg_temp

                # Custom rendering for block elements
                if data == "\u2588":
                    painter.fillRect(rect, fg_color)
                    x += 1
                    continue
                elif data == "\u2580":
                    painter.fillRect(QRectF(rect.left(), rect.top(), rect.width(), rect.height() / 2.0), fg_color)
                    x += 1
                    continue
                elif data == "\u2584":
                    hh = rect.height() / 2.0
                    painter.fillRect(QRectF(rect.left(), rect.top() + hh, rect.width(), rect.height() - hh), fg_color)
                    x += 1
                    continue
                elif data == "\u258c":
                    painter.fillRect(QRectF(rect.left(), rect.top(), rect.width() / 2.0, rect.height()), fg_color)
                    x += 1
                    continue
                elif data == "\u2590":
                    hw = rect.width() / 2.0
                    painter.fillRect(QRectF(rect.left() + hw, rect.top(), rect.width() - hw, rect.height()), fg_color)
                    x += 1
                    continue

                # Normal text rendering
                # Skip pure background spaces
                if data == " ":
                    x += 1
                    continue

                font_key = (char['bold'], char['italics'], char['underline'], char['strikethrough'])
                if font_key != last_font_key:
                    if font_key == (False, False, False, False):
                        painter.setFont(self.terminal_font)
                    else:
                        if font_key not in self._font_cache:
                            f = QFont(self.terminal_font)
                            f.setBold(char['bold'])
                            f.setItalic(char['italics'])
                            f.setUnderline(char['underline'])
                            f.setStrikeOut(char['strikethrough'])
                            self._font_cache[font_key] = f
                        painter.setFont(self._font_cache[font_key])
                    last_font_key = font_key

                if fg_color != last_pen_color:
                    painter.setPen(fg_color)
                    last_pen_color = fg_color

                is_wide = char.get('width', 1) == 2
                
                # If wide character or non-ASCII, draw individually
                if is_wide or ord(data) > 127:
                    char_real_width = self.metrics.horizontalAdvance(data)
                    cell_width = self.char_width * 2 if is_wide else self.char_width
                    x_offset = rect.left() + (cell_width - char_real_width) / 2
                    painter.drawText(QPointF(x_offset, rect.top() + self.ascent), data)
                    x += (2 if is_wide else 1)
                    continue
                    
                # Otherwise, it's an ASCII width-1 char. Group consecutive identical styles!
                segment_text = data
                start_x = x
                x += 1
                
                while x < self.cols:
                    next_char = line[x]
                    if not next_char or next_char['data'] in ("", None):
                        break
                    ndata = next_char['data']
                    if ndata in ("\u2588", "\u2580", "\u2584", "\u258c", "\u2590"):
                        break
                    
                    if next_char.get('width', 1) == 2 or ord(ndata) > 127:
                        break
                        
                    if next_char['fg'] != char['fg'] or next_char['bg'] != char['bg'] or next_char['reverse'] != char['reverse']:
                        break
                    if next_char['bold'] != char['bold'] or next_char['italics'] != char['italics'] or next_char['underline'] != char['underline'] or next_char['strikethrough'] != char['strikethrough']:
                        break
                    if self._is_selected(y, x, sel_range) != is_sel:
                        break
                        
                    segment_text += ndata
                    x += 1
                
                painter.drawText(
                    QPointF(self.padding + start_x * self.char_width, rect.top() + self.ascent),
                    segment_text
                )

        if (
            self.scroll_offset == 0
            and self.vt.cursor_visible
            and min_y <= self.vt.cursor_y <= max_y
            and 0 <= self.vt.cursor_x < self.cols
        ):
            top = int(self.padding + self.vt.cursor_y * self.char_height)
            bottom = int(self.padding + (self.vt.cursor_y + 1) * self.char_height)
            left = int(self.padding + self.vt.cursor_x * self.char_width)
            right = int(self.padding + (self.vt.cursor_x + 1) * self.char_width)
            cursor_rect = QRectF(left, top, right - left, bottom - top)
            painter.fillRect(cursor_rect, QColor(255, 255, 255, 128))
