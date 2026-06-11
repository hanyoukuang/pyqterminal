# Changelog

## [0.2.3] — 2026-06-11

### Fixed
- Windows: Prevent process crash when pressing Ctrl+C inside TUI applications (e.g. OpenCode) by ignoring `SIGINT` on Windows in the GUI launcher and widget, allowing conpty to handle the event.
- Session Restart: Recreate the `PtyTerminal` instance when restarting a terminal session to prevent `spawn_shell` from being called on a dead PTY instance, avoiding process crash/hang.
- Guarded `self._term` calls: Added try-except blocks to `resizeEvent`, `_change_font_size`, `wheelEvent`, and `_selected_text` to prevent `RuntimeError` crashes when interacting with a closed/dead PTY.

### Changed
- Upgraded `pyqterminal` version to `0.2.3`.

## [0.2.2] — 2026-06-08

### Changed
- Upgraded `par-term-emu-core-rust` to ≥0.42.4 — fixes `has_updates_since()` counter stall on Windows Ctrl+C (#60, #61).
- Removed Windows cursor-polling fallback and `_stale_polls` forced-flush workaround, no longer needed after upstream fix.
- `_poll_updates()` simplified: the `elif sys.platform == "win32"` branch and stale-poll counter logic removed.

### Documentation
- `ERRORS.md` — added error #11 documenting the Windows Ctrl+C freeze root cause and resolution.

## [0.2.1] — 2026-06-08

### Added
- Session restart: press any key after shell exits to spawn a new session.
- Debug logging at 7 key points (PTY write, resize, font size, alt screen, OSC bridge).
- Unit tests: 38 for `InputHandler`, 20 for `block_chars`.

### Changed
- Log level raised from `INFO` to `DEBUG` for full diagnostic output.
- `contextlib.suppress` replaces bare `try/except/pass` in hot paths.

### Added (tooling)
- `ruff` linter/formatter with E/W/F/I/B/C4/SIM/UP rulesets.
- `mypy` type checker with PySide6 `attr-defined` suppression.
- `basedpyright` type checker with `basic` mode, `reportAttributeAccessIssue` disabled.

### Changed (refactor)
- `_draw_block_fill()` extracted to `terminal/block_chars.py` (55 lines).
- Font candidates, `_pick_monospace_font()`, and default colors extracted to `terminal/theme.py` (35 lines).
- `widget.py` reduced from 1088 to 1048 lines.

### Documentation
- `CODING_STANDARDS.md` — PEP8, code splitting, comments, implementation, logging, testing, Git.
- `HISTORY.md` — external library change history and class/method addition timeline.

## [0.2.0] — 2026-06-05

### Added
- Background color propagation (`_BackgroundPropagator`) for unwritten cells in TUI apps.
- OSC 7 (current directory), OSC 9/777 (notifications), OSC 52 (clipboard) bridge.
- `title_changed`, `process_exited`, `bell_rang`, `selection_copied`, `notification_received`, `cwd_changed`, `progress_changed` signals.
- Mouse event forwarding to PTY when terminal apps enable mouse tracking.
- Context menu with Copy, Paste, Zoom In/Out/Reset.

### Fixed
- Windows: has_updates_since unreliable → fallback to cursor position polling.
- Windows: synchronized_updates stall → flush after 60 stale polls (1s).
- PTY write RuntimeError on session end → guarded with `_session_ended` flag.
- BCE (Background Color Erase) fixed upstream in par-term-emu-core-rust v0.42.3.

### Changed
- Upgraded to `par-term-emu-core-rust` ≥ 0.42.3 for BCE support.

## [0.1.4] — 2026-06-04

### Added
- Mouse tracking support: when terminal applications enable mouse tracking (CSI ? 1000h), mouse press/move/release events are forwarded to the PTY as X10-encoded escape sequences with Shift/Alt/Ctrl modifier support.

## [0.1.3] — 2026-06-04

### Fixed
- Nerd Font icons rendered as solid silhouettes instead of proper shapes with cutouts. Switched from `QPainter.drawText()` to `QPainterPath.addText()` + `drawPath()` for correct even-odd fill rule preserving glyph counters.
- Jagged edges after drawPath fix resolved by enabling `QPainter.Antialiasing` on text paths.
- Font hinting changed from `PreferFullHinting` to `PreferVerticalHinting` to prevent Nerd Font counter shapes from being collapsed by aggressive grid-fitting.

### Changed
- Added comprehensive terminal test suite (4 scripts from Alacritty + original demo).

## [0.1.2] — 2026-06-04

### Fixed
- Scrollback rendering inverted (vertical mirroring) when scrolling back to view history. Scrollback lines now display in correct chronological order (oldest at top, newest at bottom).
- Block characters (U+2580–U+259F, e.g. `█`) now rendered as filled rectangles instead of font glyphs, eliminating sub-pixel gaps between adjacent cells.

### Changed
- Removed unused `pyfiglet` dependency from pyproject.toml.
- Added `[build-system]` section (hatchling) for PEP 517 compliance.
- Added `Framework :: PySide6`, `Framework :: Qt`, `Typing :: Typed` classifiers.
- `main.py` simplified to a thin launcher; CLI logic moved to `terminal/__main__.py`.

## [0.1.1] — 2026-06-04

### Changed
- Relaxed Python requirement from 3.12.13 to >=3.12.
- Fixed PyPI classifier for terminal topic.

## [0.1.0] — 2026-06-03

### Added
- Initial release: cross-platform terminal emulator with Rust backend and PySide6 frontend.
- VT520 escape sequence parsing via `par-term-emu-core-rust` (alacritty `vte` crate).
- Full SGR attribute rendering: bold, italic, underline (5 styles), reverse video, dim, blink, strikethrough, hidden text.
- CJK double-width character support.
- Nerd Font icon glyph rendering.
- Text selection with auto-copy, right-click context menu, scrollback with wheel.
- Clipboard integration (Cmd+C/V macOS, Ctrl+Shift+C/V Linux/Windows).
- Font zoom (Ctrl++/Ctrl+-/Ctrl+0, 6–32pt).
- Direct QPainter rendering (no QPixmap double-buffer, Retina/HiDPI safe).
- Display-only mode (`--display`) for piping escape sequences from external sources.
- IME (Input Method) support for CJK input.
- Mouse wheel forwarding to PTY when mouse tracking is active.
- Window title sync with shell.
