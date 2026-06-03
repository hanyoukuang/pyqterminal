# AGENTS.md

## Setup & Commands

- **Python:** 3.12.13 exactly (`.python-version`). Required by `par-term-emu-core-rust` prebuilt wheels.
- **Package manager:** `uv` (not pip). `uv sync` to install deps. `uv add <pkg>` to add.
- **Run interactive:** `uv run python main.py`
- **Run display-only:** `uv run python main.py --display` (reads escape sequences from stdin)
- **Lint/format/test:** None configured yet. `tests/` directory exists but is empty.

## Architecture

A cross-platform terminal emulator with a Rust backend and PySide6 frontend. Two modes:

```
# Interactive mode (PtyTerminal — spawns shell, PTY I/O)
main.py → TerminalWidget → PtyTerminal (Rust, PTY + parser)
              ├── InputHandler (QKeyEvent → bytes)
              └── QPainter rendering directly in paintEvent()

# Display-only mode (Terminal — headless, external feed)
main.py → TerminalWidget → Terminal (Rust, parser only, no PTY)
              ├── feed() reads stdin / programmatic input
              └── QPainter rendering directly in paintEvent()
```

- **Backend:** `par_term_emu_core_rust` — two classes:
  - `PtyTerminal` — spawns shell via `spawn_shell()`, handles PTY I/O, internal `vte` parser, buffer, colors, cursor, scrollback.
  - `Terminal` — headless parser-only. Use `process_str(data)` to feed escape sequences. Used in `--display` mode.
- **Frontend:** `terminal/widget.py` (596 lines) — TerminalWidget. Core method is `_render_cells()` which handles ALL SGR attribute rendering in a single loop. Top-level rendering flow: `paintEvent()` → `_draw_row()` → `_draw_live_row()` / `_draw_scrollback_row()` → `_render_cells()`.
- **Input:** `terminal/input_handler.py` (103 lines) — `InputHandler.encode(QKeyEvent) → bytes | None`. Static method, class-level `_KEY_SEQUENCES` dict.
- **No QPixmap double buffer** — removed due to Retina/HiDPI devicePixelRatio issues (Error #5 in ERRORS.md). Render directly on the widget's QPainter in `paintEvent()`.

## Critical API Gotchas (read ERRORS.md first)

These are real API names discovered via `dir()`, not from documentation — the design doc (`DESIGN.md`) contains speculative API names that differ from reality.

| Expectation (wrong) | Reality |
|---|---|
| `get_cell_char(row, col)` | `get_line_cells(row)` returns `list[(char, fg, bg, attrs), ...]` for all cols. For plain text: use `get_line(row)` → `str`. |
| `damage_regions_since(gen)` | Not used. Code polls with `has_updates_since(gen)` + `update_generation()`, then redraws all rows on each update. |
| `process_str()` on PtyTerminal | Only exists on headless `Terminal`. PtyTerminal reads PTY internally via `spawn_shell()`. Use `Terminal.process_str()` in display-only mode or `widget.feed()`. |
| Integer cursor style | `cursor_style()` returns `CursorStyle` enum (e.g. `CursorStyle.BlinkingBlock`, `CursorStyle.SteadyUnderline`). |
| `write_str()` takes bytes | `write_str()` takes `str`. Use `write()` for `bytes`. InputHandler returns `bytes`, so `_term.write(data)` is used. |
| `resize(rows, cols)` | Code calls `_term.resize(self._cols, self._rows)` i.e. `(cols, rows)` order. If resize behaves unexpectedly, verify actual parameter order via `dir()`. |

## Rendering Rules (from hard-won fixes)

The core rendering logic lives in `_render_cells(painter, cells, y, display_row)`. Every SGR attribute is handled in ONE loop. **Do not split or reorder these checks.**

1. **Background fill BEFORE space check.** Space characters with colored backgrounds must have the background drawn. `fillRect` happens before `if is_space: continue`. Do not reorder.
2. **No QPixmap.** Render directly in `paintEvent()` via `QPainter(self)`. Qt handles devicePixelRatio automatically.
3. **Font selection** tries Nerd Fonts first, then system fonts: `MesloLGS NF → JetBrainsMono Nerd Font → FiraCode Nerd Font → CaskaydiaCove Nerd Font → Hack Nerd Font → DejaVuSansMono Nerd Font → SF Mono → JetBrains Mono → Fira Code → Menlo → Courier New → monospace`. Falls back to `"monospace"` if none found.
4. **Reverse video (SGR 7).** `attrs.reverse` — when `True`, swap fg and bg colors with proper default fallbacks. The library does NOT pre-swap; the renderer is responsible. Missing this causes nano/tmux bars to render with invisible background.
5. **Hidden text (SGR 8).** `attrs.hidden` — show background only, skip text. Used for password prompts. Place check after background fill, before text draw.
6. **Wide chars (CJK).** `attrs.wide_char` and `attrs.wide_char_spacer` — skip spacer cells entirely (they're covered by the preceding wide char's 2× cell width). Wide chars use `cell_w = self._cell_w * 2`.
7. **Blink (SGR 5).** `attrs.blink` — uses `_blink_visible` flag toggled by cursor timer (~530ms). Hide text during blink-off phase.
8. **Dim (SGR 2).** `attrs.dim` — reduce fg RGB by half (`c // 2`).
9. **Bold & Italic.** Pre-built QFont variants (`_font_bold`, `_font_italic`, `_font_bold_italic`) are selected based on `attrs.bold` / `attrs.italic`. Font is reset to `self._font` at the end of `_render_cells`.
10. **Strikethrough (SGR 9).** `attrs.strikethrough` — horizontal line at cell midpoint (`cell_h // 2`).
11. **Underline styles (SGR 4:N).** `attrs.underline_style` (UnderlineStyle enum): Straight, Double (two lines), Curly (dashed approx), Dotted (Qt.DotLine), Dashed (Qt.DashLine).

## Display-Only Mode

- Activated via `--display` flag or `TerminalWidget(display_only=True)`.
- Uses headless `Terminal` (not `PtyTerminal`). No PTY, no `spawn_shell()`.
- Feed data via `widget.feed(string)` or pipe stdin (polled via `QTimer` every 50ms from `main.py`).
- In this mode: `_poll_timer` is not started, `keyPressEvent` does not send input, paste is disabled.
- Calling `start_shell()` or `feed()` on the wrong mode raises `RuntimeError`.

## Scrollback

- `_scroll_offset` tracks how far back the user has scrolled (0 = live view).
- `scrollback_line(idx)` returns cell data (same format as `get_line_cells`) for scrollback rows.
- `scrollback_len()` returns total scrollback buffer size.
- When scrolled back and new output arrives, a yellow indicator bar (3 cells wide, 3px tall) appears at the bottom-right (`_unseen_output` flag).
- Shift+PageUp/PageDown scrolls by `_rows // 2` lines. Mouse wheel scrolls with granularity smoothing via `_wheel_accum` (threshold: `_cell_h`).

## Selection & Clipboard

- Mouse drag selects text (row, col based). `mousePressEvent` starts, `mouseMoveEvent` extends, `mouseReleaseEvent` auto-copies.
- `_selected_text()` extracts text using `get_line()` for live rows and `scrollback_line()` for scrollback rows. Joins lines with `\n`.
- Cmd+C (macOS) / Ctrl+Shift+C copies existing selection.
- Cmd+V (macOS) / Ctrl+Shift+V pastes clipboard via `_term.write_str(text)`.
- Middle-click pastes clipboard. Right-click context menu: Copy, Paste, Zoom In/Out/Reset.
- Selection is cleared on keyboard input (`_clear_selection()` in `keyPressEvent`).

## Zoom

- Ctrl++ / Ctrl+- / Ctrl+0 (macOS) or Ctrl+Shift++ / Ctrl+Shift+- (other platforms) change font size.
- Min size 6pt, max 32pt. Default size is 13pt.
- `_change_font_size(delta)` rebuilds all font variants, recalculates cell dimensions, calls `_term.resize()`, and triggers `update()`.

## Window Title Sync

- `_poll_updates()` checks `self._term.title()` each frame (16ms). If title differs from `windowTitle()`, sets it. Wrapped in try/except (title() may not be supported on all platforms).

## Cursor

- Cursor timer toggles both `_cursor_visible` and `_blink_visible` every 530ms.
- `_draw_cursor()` queries `cursor_position()` and `cursor_style()`.
- Cursor styles handled: Block (default), Underline, Bar — each with Blinking and Steady variants (6 total via `CursorStyle` enum). Not drawn when scrolled back.

## Design Docs

- `DESIGN.md` — Architecture design doc (Chinese). The architecture sections (§4-§6) reflect the intended design, but the actual implementation has simplified (no damage_regions, no QPixmap buffer, monolithic `_render_cells` instead of per-row draw methods). The API names in the design doc code examples are speculative — trust the actual code over them.
- `ERRORS.md` — Error log with 7 documented mistakes and their root causes. **Read this before touching `widget.py`.** Contains PySide6 and par-term-emu-core-rust trap checklists.
