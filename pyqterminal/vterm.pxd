from libc.stdint cimport uint32_t, uint8_t
from libc.stddef cimport size_t

cdef extern from "vterm.h":
    ctypedef struct VTerm:
        pass
    ctypedef struct VTermScreen:
        pass
    ctypedef struct VTermState:
        pass
        
    ctypedef struct VTermPos:
        int row
        int col

    ctypedef struct VTermRect:
        int start_row
        int end_row
        int start_col
        int end_col

    ctypedef struct VTermColorRGB:
        uint8_t type
        uint8_t red
        uint8_t green
        uint8_t blue
        
    ctypedef struct VTermColorIndexed:
        uint8_t type
        uint8_t idx
        
    ctypedef union VTermColor:
        uint8_t type
        VTermColorRGB rgb
        VTermColorIndexed indexed

    cdef enum VTermColorType:
        VTERM_COLOR_DEFAULT_FG = 0
        VTERM_COLOR_DEFAULT_BG = 1
        VTERM_COLOR_INDEXED    = 2
        VTERM_COLOR_RGB        = 3

    ctypedef struct VTermScreenCellAttrs:
        unsigned int bold
        unsigned int underline
        unsigned int italic
        unsigned int blink
        unsigned int reverse
        unsigned int conceal
        unsigned int strike
        unsigned int font
        unsigned int dwl
        unsigned int dhl
        unsigned int small
        unsigned int baseline

    ctypedef struct VTermScreenCell:
        uint32_t chars[6]
        char width
        VTermScreenCellAttrs attrs
        VTermColor fg
        VTermColor bg

    ctypedef struct VTermScreenCallbacks:
        int (*damage)(VTermRect rect, void *user)
        int (*moverect)(VTermRect dest, VTermRect src, void *user)
        int (*movecursor)(VTermPos pos, VTermPos oldpos, int visible, void *user)
        int (*settermprop)(int prop, void *val, void *user)
        int (*bell)(void *user)
        int (*resize)(int rows, int cols, void *user)
        int (*sb_pushline)(int cols, const VTermScreenCell *cells, void *user)
        int (*sb_popline)(int cols, VTermScreenCell *cells, void *user)

    VTerm* vterm_new(int rows, int cols)
    void vterm_free(VTerm *vt)
    void vterm_set_utf8(VTerm *vt, int is_utf8)
    
    void vterm_input_write(VTerm *vt, const char *bytes, size_t len)
    size_t vterm_output_get_buffer_current(VTerm *vt)
    size_t vterm_output_read(VTerm *vt, char *buffer, size_t len)

    VTermScreen* vterm_obtain_screen(VTerm *vt)
    void vterm_screen_enable_altscreen(VTermScreen *screen, int altscreen)
    void vterm_screen_set_callbacks(VTermScreen *screen, const VTermScreenCallbacks *callbacks, void *user)
    void vterm_screen_reset(VTermScreen *screen, int hard)
    int vterm_screen_get_cell(const VTermScreen *screen, VTermPos pos, VTermScreenCell *cell)
    void vterm_screen_convert_color_to_rgb(const VTermScreen *screen, VTermColor *col)

    VTermState* vterm_obtain_state(VTerm *vt)
    void vterm_state_reset(VTermState *state, int hard)

    void vterm_set_size(VTerm *vt, int rows, int cols)

    # Input
    ctypedef enum VTermModifier:
        VTERM_MOD_NONE  = 0x00
        VTERM_MOD_SHIFT = 0x01
        VTERM_MOD_ALT   = 0x02
        VTERM_MOD_CTRL  = 0x04

    ctypedef enum VTermKey:
        VTERM_KEY_NONE = 0
        VTERM_KEY_ENTER = 1
        VTERM_KEY_TAB = 2
        VTERM_KEY_BACKSPACE = 3
        VTERM_KEY_ESCAPE = 4
        VTERM_KEY_UP = 5
        VTERM_KEY_DOWN = 6
        VTERM_KEY_LEFT = 7
        VTERM_KEY_RIGHT = 8
        # Add other keys as needed

    void vterm_keyboard_unichar(VTerm *vt, uint32_t c, VTermModifier mod)
    void vterm_keyboard_key(VTerm *vt, VTermKey key, VTermModifier mod)
    void vterm_mouse_move(VTerm *vt, int row, int col, VTermModifier mod)
    void vterm_mouse_button(VTerm *vt, int button, int pressed, VTermModifier mod)

    # Encoding
    void vterm_color_rgb(VTermColor *col, uint8_t red, uint8_t green, uint8_t blue)
    void vterm_color_indexed(VTermColor *col, uint8_t idx)
