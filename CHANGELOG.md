# Changelog

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
