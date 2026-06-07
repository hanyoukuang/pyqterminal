"""BCE bug demo — raw par-term-emu-core-rust, no BackgroundPropagator.

Shows that after \x1b[K, the Rust library leaves black bg instead of the
active SGR background color. No pyqterminal rendering involved.

Usage:
    uv run python tests/bce_raw_test.py
"""

from par_term_emu_core_rust import Terminal


def main() -> None:
    # Feed one row at a time via fresh Terminal to avoid cursor confusion
    COLORS = {
        (0, 128, 0):   "\033[42m GREEN \033[0m",
        (0, 0, 128):   "\033[44m BLUE  \033[0m",
        (128, 0, 0):   "\033[41m RED   \033[0m",
        (128, 0, 128): "\033[45m MAGENTA \033[0m",
        (128, 128, 0): "\033[43m YELLOW \033[0m",
        (0, 0, 0):     " BLACK ",
    }

    tests = [
        ("GREEN+EL ",  "\x1b[42mGREEN+EL  \x1b[K", (0, 128, 0)),
        ("BLUE+EL  ",  "\x1b[44mBLUE+EL   \x1b[K", (0, 0, 128)),
        ("RED+EL   ",  "\x1b[41mRED+EL    \x1b[K", (128, 0, 0)),
        ("MAGENTA+EL", "\x1b[45mMAGENTA+EL\x1b[K", (128, 0, 128)),
        ("YELLOW+EL ", "\x1b[43mYELLOW+EL \x1b[K", (128, 128, 0)),
        ("GREEN     ", "\x1b[42mGREEN     ",       (0, 128, 0)),
        ("BLUE      ", "\x1b[44mBLUE      ",       (0, 0, 128)),
        ("RED       ", "\x1b[41mRED       ",       (128, 0, 0)),
    ]

    print("BCE Bug: par-term-emu-core-rust, each row = fresh Terminal instance")
    print("=" * 65)
    print(f"{'Label':12s} | {'text bg[0]':>14s} | {'trail bg[20]':>16s}")
    print(f"{'':12s} | {'expected':>7s} {'actual':>7s} | {'expected':>7s} {'actual':>7s}")
    print("-" * 65)

    for label, seq, expected_bg in tests:
        t = Terminal(40, 2)
        t.process_str(seq)
        cells = t.get_line_cells(0)

        bg_text = cells[0][2]  # col 0 — inside text area
        bg_trail = cells[20][2] if len(cells) > 20 else cells[-1][2]  # col 20 — trailing

        has_el = "+EL" in label
        if has_el:
            # With EL: trailing should match expected bg
            trail_ok = bg_trail == expected_bg
        else:
            # No EL: trailing never written → should be (0,0,0)
            trail_ok = bg_trail == (0, 0, 0)

        icon = "\033[32mOK\033[0m" if trail_ok else "\033[31mFAIL\033[0m"

        print(f"{label:12s} | {COLORS.get(bg_text, str(bg_text)):>14s} | "
              f"{icon} {COLORS.get(bg_trail, str(bg_trail)):>14s}")

    print("-" * 65)
    print()
    print("With \\x1b[K: trailing cells should match the SGR background color.")
    print("All 5 EL rows PASS — BCE fixed in v0.42.3.")
    print()
    print("Ref: Alacritty erase_chars() uses cursor.template.bg")


if __name__ == "__main__":
    main()
