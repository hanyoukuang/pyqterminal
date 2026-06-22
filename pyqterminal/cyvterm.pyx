# cython: language_level=3
from pyqterminal.vterm cimport *
from libc.stdlib cimport malloc, free
cimport cython
from collections import deque

cdef int on_damage(VTermRect rect, void *user) noexcept with gil:
    cdef TerminalScreen screen = <TerminalScreen>user
    screen.mark_dirty(rect.start_row, rect.end_row)
    return 1

cdef int on_moverect(VTermRect dest, VTermRect src, void *user) noexcept with gil:
    cdef TerminalScreen screen = <TerminalScreen>user
    screen.mark_dirty(dest.start_row, dest.end_row)
    return 1

cdef int on_movecursor(VTermPos pos, VTermPos oldpos, int visible, void *user) noexcept with gil:
    cdef TerminalScreen screen = <TerminalScreen>user
    screen.cursor_x = pos.col
    screen.cursor_y = pos.row
    screen.cursor_visible = visible
    screen.mark_dirty(oldpos.row, oldpos.row + 1)
    screen.mark_dirty(pos.row, pos.row + 1)
    return 1

cdef int on_sb_pushline(int cols, const VTermScreenCell *cells, void *user) noexcept with gil:
    cdef TerminalScreen screen = <TerminalScreen>user
    cdef size_t line_size = cols * sizeof(VTermScreenCell)
    cdef bytes raw_line = (<char*>cells)[:line_size]
    screen.push_scrollback((cols, raw_line))
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
    cdef public int cursor_x
    cdef public int cursor_y
    cdef public bint cursor_visible
    cdef public set dirty_rows
    cdef object _history
    cdef int history_size
    
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
        
        vterm_screen_set_callbacks(self.screen, &cb, <void*>self)
        
        self.cursor_x = 0
        self.cursor_y = 0
        self.cursor_visible = True
        self.dirty_rows = set()
        self._history = deque(maxlen=history_size)
        self.history_size = history_size
        
    def __dealloc__(self):
        if self.vt != NULL:
            vterm_free(self.vt)
            
    cdef void mark_dirty(self, int start_row, int end_row):
        for r in range(start_row, end_row):
            self.dirty_rows.add(r)
            
    cdef void push_scrollback(self, tuple line_data):
        self._history.append(line_data)
        
    def history_len(self):
        return len(self._history)
        
    def get_history_line(self, int index):
        cdef tuple line_data = self._history[index]
        cdef int cols = line_data[0]
        cdef bytes raw_line = line_data[1]
        cdef const char* raw_ptr = raw_line
        cdef const VTermScreenCell* cells = <const VTermScreenCell*>raw_ptr
        
        cdef list line = []
        cdef int i, j
        cdef uint32_t char_code
        cdef VTermColor fg, bg
        
        for i in range(cols):
            cell_data = {}
            chars_str = ""
            for j in range(6):
                char_code = cells[i].chars[j]
                if char_code == 0 or char_code > 0x10FFFF:
                    break
                chars_str += chr(char_code)
                
            cell_data['data'] = chars_str
            cell_data['width'] = cells[i].width
            cell_data['bold'] = cells[i].attrs.bold
            cell_data['underline'] = cells[i].attrs.underline
            cell_data['italics'] = cells[i].attrs.italic
            cell_data['strikethrough'] = cells[i].attrs.strike
            cell_data['reverse'] = cells[i].attrs.reverse
            
            fg = cells[i].fg
            bg = cells[i].bg
            vterm_screen_convert_color_to_rgb(self.screen, &fg)
            vterm_screen_convert_color_to_rgb(self.screen, &bg)
            
            cell_data['fg'] = _convert_color(fg)
            cell_data['bg'] = _convert_color(bg)
            
            line.append(cell_data)
            
        return line
        
    def feed(self, bytes data):
        cdef const char* c_string = data
        vterm_input_write(self.vt, c_string, len(data))
        
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
