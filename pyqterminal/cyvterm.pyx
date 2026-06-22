# cython: language_level=3
from pyqterminal.vterm cimport *
from libc.stdlib cimport malloc, free
from libc.string cimport memcpy
cimport cython

cdef struct ScrollbackLine:
    int cols
    VTermScreenCell *cells

cdef struct ScreenCallbackData:
    void *py_screen_ptr
    ScrollbackLine* history_buf
    int hist_head
    int hist_tail
    int hist_count
    int history_size
    bint* dirty_rows
    int cursor_x
    int cursor_y
    int cursor_visible

cdef int on_damage(VTermRect rect, void *user) noexcept nogil:
    cdef ScreenCallbackData *cb_data = <ScreenCallbackData*>user
    cdef int r
    for r in range(rect.start_row, rect.end_row):
        cb_data.dirty_rows[r] = True
    return 1

cdef int on_moverect(VTermRect dest, VTermRect src, void *user) noexcept nogil:
    cdef ScreenCallbackData *cb_data = <ScreenCallbackData*>user
    cdef int r
    for r in range(dest.start_row, dest.end_row):
        cb_data.dirty_rows[r] = True
    return 1

cdef int on_movecursor(VTermPos pos, VTermPos oldpos, int visible, void *user) noexcept nogil:
    cdef ScreenCallbackData *cb_data = <ScreenCallbackData*>user
    cb_data.cursor_x = pos.col
    cb_data.cursor_y = pos.row
    cb_data.cursor_visible = visible
    cb_data.dirty_rows[oldpos.row] = True
    cb_data.dirty_rows[pos.row] = True
    return 1

cdef int on_sb_pushline(int cols, const VTermScreenCell *cells, void *user) noexcept nogil:
    cdef ScreenCallbackData *cb_data = <ScreenCallbackData*>user
    cdef ScrollbackLine line
    line.cols = cols
    line.cells = <VTermScreenCell*>malloc(cols * sizeof(VTermScreenCell))
    memcpy(line.cells, cells, cols * sizeof(VTermScreenCell))
    
    if cb_data.hist_count == cb_data.history_size:
        free(cb_data.history_buf[cb_data.hist_head].cells)
        cb_data.history_buf[cb_data.hist_head] = line
        cb_data.hist_head = (cb_data.hist_head + 1) % cb_data.history_size
        cb_data.hist_tail = (cb_data.hist_tail + 1) % cb_data.history_size
    else:
        cb_data.history_buf[cb_data.hist_tail] = line
        cb_data.hist_tail = (cb_data.hist_tail + 1) % cb_data.history_size
        cb_data.hist_count += 1
    return 1

cdef _convert_color(VTermColor color):
    if color.type & 0x02:
        return "default_fg"
    elif color.type & 0x04:
        return "default_bg"
    elif color.type & 0x01:
        return f"index:{color.indexed.idx}"
    else:
        return f"#{color.rgb.red:02x}{color.rgb.green:02x}{color.rgb.blue:02x}"

cdef VTermScreenCallbacks cb
cb.damage = on_damage
cb.moverect = on_moverect
cb.movecursor = on_movecursor
cb.settermprop = NULL
cb.bell = NULL
cb.resize = NULL
cb.sb_pushline = on_sb_pushline
cb.sb_popline = NULL

cdef class TerminalScreen:
    cdef VTerm *vt
    cdef VTermScreen *screen
    cdef VTermState *state
    cdef public int rows
    cdef public int cols
    cdef ScreenCallbackData *cb_data
    
    def __cinit__(self, int rows, int cols, int history_size=10000):
        self.rows = rows
        self.cols = cols
        self.vt = vterm_new(rows, cols)
        vterm_set_utf8(self.vt, 1)
        
        self.state = vterm_obtain_state(self.vt)
        vterm_state_reset(self.state, 1)
        
        self.screen = vterm_obtain_screen(self.vt)
        vterm_screen_enable_altscreen(self.screen, 1)
        vterm_screen_reset(self.screen, 1)
        
        self.cb_data = <ScreenCallbackData*>malloc(sizeof(ScreenCallbackData))
        self.cb_data.py_screen_ptr = <void*>self
        self.cb_data.history_size = history_size
        self.cb_data.history_buf = <ScrollbackLine*>malloc(history_size * sizeof(ScrollbackLine))
        self.cb_data.hist_head = 0
        self.cb_data.hist_tail = 0
        self.cb_data.hist_count = 0
        self.cb_data.dirty_rows = <bint*>malloc(rows * sizeof(bint))
        cdef int i
        for i in range(rows):
            self.cb_data.dirty_rows[i] = False
        self.cb_data.cursor_x = 0
        self.cb_data.cursor_y = 0
        self.cb_data.cursor_visible = True
        
        vterm_screen_set_callbacks(self.screen, &cb, <void*>self.cb_data)
        
    def __dealloc__(self):
        cdef int i, idx
        if self.cb_data != NULL:
            for i in range(self.cb_data.hist_count):
                idx = (self.cb_data.hist_head + i) % self.cb_data.history_size
                free(self.cb_data.history_buf[idx].cells)
            free(self.cb_data.history_buf)
            free(self.cb_data.dirty_rows)
            free(self.cb_data)
            
        if self.vt != NULL:
            vterm_free(self.vt)
            
    @property
    def cursor_x(self):
        return self.cb_data.cursor_x

    @property
    def cursor_y(self):
        return self.cb_data.cursor_y

    @property
    def cursor_visible(self):
        return self.cb_data.cursor_visible

    @property
    def dirty_rows(self):
        cdef set dirty = set()
        cdef int i
        for i in range(self.rows):
            if self.cb_data.dirty_rows[i]:
                dirty.add(i)
                self.cb_data.dirty_rows[i] = False
        return dirty
            
    def history_len(self):
        return self.cb_data.hist_count
        
    cdef list _build_runs(self, VTermScreenCell* cells, int cols):
        cdef list runs = []
        cdef int i, j
        cdef uint32_t char_code
        cdef VTermColor fg, bg
        cdef str chars_str
        
        cdef str run_data = ""
        cdef int run_width = 0
        cdef VTermScreenCell* first_cell = NULL
        cdef VTermScreenCell* cell
        cdef bint is_empty = False
        cdef bint prev_empty = False
        cdef bint is_block = False
        cdef bint first_is_block = False
        cdef bint merge
        
        for i in range(cols):
            cell = &cells[i]
            char_code = cell.chars[0]
            is_empty = (char_code == 0)
            is_block = (char_code == 0x2588 or char_code == 0x2580 or char_code == 0x2584)
            
            merge = False
            if first_cell != NULL:
                first_is_block = (first_cell.chars[0] == 0x2588 or first_cell.chars[0] == 0x2580 or first_cell.chars[0] == 0x2584)
                if is_block or first_is_block:
                    merge = False
                else:
                    if (cell.attrs.bold == first_cell.attrs.bold and
                        cell.attrs.underline == first_cell.attrs.underline and
                        cell.attrs.italic == first_cell.attrs.italic and
                        cell.attrs.strike == first_cell.attrs.strike and
                        cell.attrs.reverse == first_cell.attrs.reverse and
                        cell.fg.type == first_cell.fg.type and
                        cell.bg.type == first_cell.bg.type):
                        
                        merge = True
                        if cell.fg.type == 1:
                            merge = (cell.fg.indexed.idx == first_cell.fg.indexed.idx)
                        elif cell.fg.type == 2:
                            merge = (cell.fg.rgb.red == first_cell.fg.rgb.red and
                                     cell.fg.rgb.green == first_cell.fg.rgb.green and
                                     cell.fg.rgb.blue == first_cell.fg.rgb.blue)
                            
                        if merge:
                            if cell.bg.type == 1:
                                merge = (cell.bg.indexed.idx == first_cell.bg.indexed.idx)
                            elif cell.bg.type == 2:
                                merge = (cell.bg.rgb.red == first_cell.bg.rgb.red and
                                         cell.bg.rgb.green == first_cell.bg.rgb.green and
                                         cell.bg.rgb.blue == first_cell.bg.rgb.blue)
                                         
            if not merge and first_cell != NULL:
                fg = first_cell.fg
                bg = first_cell.bg
                vterm_screen_convert_color_to_rgb(self.screen, &fg)
                vterm_screen_convert_color_to_rgb(self.screen, &bg)
                runs.append((
                    run_data,
                    run_width,
                    _convert_color(fg),
                    _convert_color(bg),
                    first_cell.attrs.bold,
                    first_cell.attrs.italic,
                    first_cell.attrs.underline,
                    first_cell.attrs.strike,
                    first_cell.attrs.reverse
                ))
                first_cell = NULL
                run_data = ""
                run_width = 0
                
            if first_cell == NULL:
                first_cell = cell
                prev_empty = is_empty
                
            chars_str = ""
            for j in range(6):
                char_code = cell.chars[j]
                if char_code == 0 or char_code > 0x10FFFF:
                    break
                if char_code != 0xFFFFFFFF:
                    chars_str += chr(char_code)
            
            run_data += chars_str
            run_width += cell.width
            
        if first_cell != NULL:
            fg = first_cell.fg
            bg = first_cell.bg
            vterm_screen_convert_color_to_rgb(self.screen, &fg)
            vterm_screen_convert_color_to_rgb(self.screen, &bg)
            runs.append((
                run_data,
                run_width,
                _convert_color(fg),
                _convert_color(bg),
                first_cell.attrs.bold,
                first_cell.attrs.italic,
                first_cell.attrs.underline,
                first_cell.attrs.strike,
                first_cell.attrs.reverse
            ))
            
        return runs

    def get_history_line(self, int index):
        if index < 0 or index >= self.cb_data.hist_count:
            return []
        cdef int real_idx = (self.cb_data.hist_head + index) % self.cb_data.history_size
        cdef ScrollbackLine line_data = self.cb_data.history_buf[real_idx]
        return self._build_runs(line_data.cells, line_data.cols)
        
    def get_line(self, int row):
        cdef VTermPos pos
        pos.row = row
        cdef VTermScreenCell* cells = <VTermScreenCell*>malloc(self.cols * sizeof(VTermScreenCell))
        cdef int i
        for i in range(self.cols):
            pos.col = i
            vterm_screen_get_cell(self.screen, pos, &cells[i])
        cdef list runs = self._build_runs(cells, self.cols)
        free(cells)
        return runs
        
    def feed(self, bytes data):
        cdef const char* c_string = data
        cdef int length = len(data)
        with nogil:
            vterm_input_write(self.vt, c_string, length)
        
    def read_output(self):
        cdef size_t out_len = vterm_output_get_buffer_current(self.vt)
        if out_len == 0:
            return b""
        
        cdef char *buf = <char *>malloc(out_len)
        if not buf:
            raise MemoryError()
            
        cdef size_t read_len = vterm_output_read(self.vt, buf, out_len)
        cdef bytes result = buf[:read_len]
        free(buf)
        return result
        
    def get_cell(self, int row, int col):
        cdef VTermPos pos
        pos.row = row
        pos.col = col
        cdef VTermScreenCell cell
        cdef int ret = vterm_screen_get_cell(self.screen, pos, &cell)
        if not ret:
            return None
            
        vterm_screen_convert_color_to_rgb(self.screen, &cell.fg)
        vterm_screen_convert_color_to_rgb(self.screen, &cell.bg)
            
        cdef str chars_str = ""
        cdef int j
        cdef uint32_t char_code
        for j in range(6):
            char_code = cell.chars[j]
            if char_code == 0 or char_code > 0x10FFFF:
                break
            chars_str += chr(char_code)
            
        return {
            'data': chars_str,
            'width': cell.width,
            'bold': cell.attrs.bold,
            'underline': cell.attrs.underline,
            'italics': cell.attrs.italic,
            'strikethrough': cell.attrs.strike,
            'reverse': cell.attrs.reverse,
            'fg': _convert_color(cell.fg),
            'bg': _convert_color(cell.bg),
        }
        
    def resize(self, int rows, int cols):
        self.rows = rows
        self.cols = cols
        vterm_set_size(self.vt, rows, cols)
        
    def reset(self):
        vterm_state_reset(self.state, 1)
        vterm_screen_reset(self.screen, 1)
        self.dirty_rows.clear()
        
    def keyboard_unichar(self, uint32_t c, int mod):
        vterm_keyboard_unichar(self.vt, c, <VTermModifier>mod)
        
    def keyboard_key(self, int key, int mod):
        vterm_keyboard_key(self.vt, <VTermKey>key, <VTermModifier>mod)
        
    def mouse_move(self, int row, int col, int mod):
        vterm_mouse_move(self.vt, row, col, <VTermModifier>mod)
        
    def mouse_button(self, int button, int pressed, int mod):
        vterm_mouse_button(self.vt, button, pressed, <VTermModifier>mod)
