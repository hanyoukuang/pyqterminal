"""Diagnostic: test PTY behavior after child process exit.

Run on Windows to check if the PTY session stays alive or dies
when a TUI app is killed via Ctrl+C. Do NOT run a TUI app first —
this tests the raw PTY behavior by sending commands programmatically.

Usage:
    uv run python tests/diagnose_pty.py
"""

import time
from par_term_emu_core_rust import PtyTerminal


def main() -> None:
    print("=== PTY Session Diagnostic ===")
    print()

    term = PtyTerminal(80, 24)

    # 1. Test basic spawn
    print("1. Spawning shell...")
    try:
        term.spawn_shell()
        print("   spawn_shell() OK")
    except Exception as e:
        print(f"   spawn_shell() FAILED: {e}")
        return

    time.sleep(1)

    # 2. Check initial state
    print("2. Initial state:")
    print(f"   is_running = {_safe(term, 'is_running')}")
    print(f"   is_alt_screen_active = {_safe(term, 'is_alt_screen_active')}")
    print(f"   child_pid = {_safe(term, 'child_pid')}")
    print(f"   title = {_safe(term, 'title')}")

    # 3. Send a simple command and read output
    print("3. Sending 'echo HELLO'...")
    try:
        term.write_str("echo HELLO\r\n")
    except Exception as e:
        print(f"   write_str FAILED: {e}")
    time.sleep(0.5)
    _print_updates(term, "After echo")

    # 4. Enter alt screen like a TUI would
    print("4. Entering alt screen (\x1b[?1049h)...")
    try:
        term.write_str("\x1b[?1049h")
    except Exception as e:
        print(f"   write_str FAILED: {e}")
    time.sleep(0.3)
    print(f"   is_alt_screen_active = {_safe(term, 'is_alt_screen_active')}")
    _print_updates(term, "In alt screen")

    # 5. Simulate Ctrl+C from inside alt screen (what happens when user
    #    presses Ctrl+C while a TUI app is in alt screen)
    print("5. Simulating Ctrl+C (sending 0x03 to PTY)...")
    try:
        term.write(b"\x03")
        print("   write(b'\\x03') OK")
    except RuntimeError as e:
        print(f"   write(b'\\x03') RuntimeError: {e}")
    except Exception as e:
        print(f"   write(b'\\x03') FAILED: {type(e).__name__}: {e}")

    time.sleep(1)

    # 6. Check state after Ctrl+C
    print("6. After Ctrl+C:")
    print(f"   is_running = {_safe(term, 'is_running')}")
    print(f"   is_alt_screen_active = {_safe(term, 'is_alt_screen_active')}")
    _print_updates(term, "After Ctrl+C")

    # 7. Try to send another command
    print("7. Sending 'echo AFTER_CTRL_C'...")
    try:
        term.write_str("echo AFTER_CTRL_C\r\n")
        print("   write_str OK")
    except RuntimeError as e:
        print(f"   write_str RuntimeError: {e}")
    except Exception as e:
        print(f"   write_str FAILED: {type(e).__name__}: {e}")

    time.sleep(0.5)
    _print_updates(term, "After second echo")

    # 8. Try a few more polls
    print("8. Polling for updates over 2 seconds...")
    gen = term.update_generation()
    for i in range(10):
        time.sleep(0.2)
        try:
            if term.has_updates_since(gen):
                gen = term.update_generation()
                print(f"   [{i}] has_updates=True, new_gen={gen}")
            else:
                print(f"   [{i}] has_updates=False")
        except RuntimeError as e:
            print(f"   [{i}] RuntimeError from has_updates_since: {e}")
            break
        except Exception as e:
            print(f"   [{i}] {type(e).__name__}: {e}")
            break

    # 9. Final state
    print("9. Final state:")
    print(f"   is_running = {_safe(term, 'is_running')}")
    print(f"   is_alt_screen_active = {_safe(term, 'is_alt_screen_active')}")
    print()
    print("=== Diagnostic complete ===")


def _safe(term, method):
    try:
        return getattr(term, method)()
    except Exception as e:
        return f"ERROR: {type(e).__name__}"


def _print_updates(term, label):
    gen = term.update_generation()
    time.sleep(0.2)
    try:
        has = term.has_updates_since(gen)
        print(f"   [{label}] has_updates={has}")
    except Exception as e:
        print(f"   [{label}] ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
