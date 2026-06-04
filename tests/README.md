# Terminal Rendering Tests

Scripts for testing pyqterminal's escape sequence rendering and SGR attribute handling.

## Usage

```bash
# Display-only mode (piped to terminal widget):
bash tests/terminal-testdrive.sh | pyqterminal --display

# Or run directly in pyqterminal interactive mode:
bash tests/terminal-testdrive.sh
```

## Scripts

| Script | Source | License | Tests |
|--------|--------|---------|-------|
| `pyqterminal-demo.sh` | Original | MIT | Logo + SGR showcase + CJK + Nerd Font + box drawing |
| `fg-bg.sh` | [Alacritty](https://github.com/alacritty/alacritty) | Apache 2.0 | fg/bg color combos + inverse (SGR 7) + hidden (SGR 8) + hid+inv |
| `colors.sh` | [Alacritty](https://github.com/alacritty/alacritty) | Apache 2.0 | All SGR attribute combos (0-8) × 8 fg × 8 bg |
| `24-bit-color.sh` | [Alacritty](https://github.com/alacritty/alacritty) / [iTerm2](https://github.com/gnachman/iTerm2) | Apache 2.0 | 24-bit true color R/G/B ramps + HSV rainbow |
| `terminal-testdrive.sh` | [@hellricer](https://gist.github.com/hellricer/e514d9615d02838244d8de74d0ab18b3) | CC0 | Truecolor gradient, text decorations, Unicode, emoji, RTL, sixel |

## Quick Smoke Test

```bash
# Run all tests in sequence with color output:
for f in tests/*.sh; do
  echo "=== $(basename $f) ==="
  bash "$f"
  echo
done | pyqterminal --display
```
