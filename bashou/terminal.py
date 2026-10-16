"""Full-screen views (the board, the starter picker, the library, the adventure, `bashou evolve`): keys
read one by one without Enter, and the terminal always given back as it was, even on a crash."""

import os
import select
import sys
import termios
import tty
from contextlib import contextmanager
from .render import ESC

# What a key means on every screen; a screen adds its own (`f` on the board).
NAMES = {"\x1b[A": "up", "\x1b[B": "down", "\x1b[C": "right", "\x1b[D": "left",
         "k": "up", "j": "down", "l": "right", "h": "left", "\r": "enter", "\n": "enter",
         "q": "quit", ESC: "quit", "\x04": "quit", "\x03": "quit"}      # Esc, Ctrl+D, Ctrl+C


def name(key, extra=None):
    """"up", "enter", "quit"…, or "" for a key that means nothing here."""
    return (extra or {}).get(key) or NAMES.get(key, "")


MOUSE_ON = f"{ESC}[?1000h{ESC}[?1003h{ESC}[?1006h"     # clicks, moves (for hover), as ESC [ < b ; x ; y M
MOUSE_OFF = f"{ESC}[?1006l{ESC}[?1003l{ESC}[?1000l"


def split_keys(data):
    """Split a read into keys: arrow escapes and mouse reports stay whole (a report cut by the read is dropped)."""
    keys, i = [], 0
    while i < len(data):
        if data.startswith(ESC + "[<", i):
            end = next((j for j in range(i + 3, len(data)) if data[j] in "Mm"), None)
            if end is None:
                break
            keys.append(data[i:end + 1])
            i = end + 1
        elif data[i] == ESC and data[i + 1:i + 2] == "[" and i + 2 < len(data):
            keys.append(data[i:i + 3])
            i += 3
        else:
            keys.append(data[i])
            i += 1
    return keys


def mouse(key):
    """("click" | "move" | "wheel_up" | "wheel_down", column, row) for a mouse report, else None. A button
    release is None: a click counts when it's pressed."""
    if not key.startswith(ESC + "[<") or not key.endswith("M"):
        return None
    try:
        button, x, y = (int(n) for n in key[3:-1].split(";"))
    except ValueError:
        return None
    if button in (64, 65):
        return ("wheel_up" if button == 64 else "wheel_down", x, y)
    if button & 32:
        return ("move", x, y)
    return ("click", x, y) if button == 0 else None


class Screen:
    """`with Screen() as screen:` the alternate screen (unless alt=False), no cursor, no line wrap
    (unless wrap=True: a long line would spill onto the next), keys without Enter, and the mouse when a
    screen asks for it (mouse=True: see mouse())."""

    def __init__(self, alt=True, wrap=False, fd=None, mouse=False):
        self.alt, self.wrap, self.mouse = alt, wrap, mouse
        self.fd = sys.stdin.fileno() if fd is None else fd
        self.old = None

    def __enter__(self):
        self.old = termios.tcgetattr(self.fd)
        sys.stdout.write((f"{ESC}[?1049h{ESC}[2J" if self.alt else "") + f"{ESC}[?25l"
                         + ("" if self.wrap else f"{ESC}[?7l") + (MOUSE_ON if self.mouse else ""))
        sys.stdout.flush()
        tty.setcbreak(self.fd)
        return self

    def __exit__(self, *_exc):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
        sys.stdout.write(f"{ESC}[0m" + (MOUSE_OFF if self.mouse else "") + ("" if self.wrap else f"{ESC}[?7h") + f"{ESC}[?25h"
                         + (f"{ESC}[?1049l" if self.alt else ""))
        sys.stdout.flush()

    def keys(self, timeout):
        """The keys pressed within `timeout` seconds (an empty list if none)."""
        if not select.select([self.fd], [], [], timeout)[0]:
            return []
        return split_keys(os.read(self.fd, 4096).decode(errors="ignore"))

    @contextmanager
    def paused(self):
        """Give the terminal back for a while (a sandbox shell), then take it again."""
        self.__exit__()
        try:
            yield
        finally:
            self.__enter__()
