"""`bashou start`: pick your starter, once. Only `bashou reset` lets you pick again."""

import os
import select
import sys
import termios
import tty

from . import creatures, render, state
from .creatures import FORM_NAMES, STARTER_BLURBS, STARTERS

ESC = "\x1b"
BOLD, DIM, RESET, REV = f"{ESC}[1m", f"{ESC}[2m", f"{ESC}[0m", f"{ESC}[7m"
KEYS = {"\x1b[C": 1, "l": 1, "\x1b[D": -1, "h": -1}
SLOT = 26


def draw(pos, breath):
    lines = [f"{BOLD}Choose your starter{RESET}  {DIM}(for good: only `bashou reset` lets you choose again){RESET}",
             "", f"{DIM}←/→ to look, Enter to choose, q to decide later{RESET}", ""]
    cols = []
    for i, line in enumerate(STARTERS):
        forms = STARTERS[line]
        pet = creatures.get(forms[0])
        cells = [[True] * pet.width for _ in range(len(pet.base) // 2)]
        sprite = render.lines(pet, ["inhale"] if breath and i == pos else [], cells)
        name = FORM_NAMES[forms[0]]
        title = f"{REV} {name} {RESET}" if i == pos else f" {name} "
        evolves = " → ".join(FORM_NAMES[f] for f in forms)
        cols.append(sprite + ["", title, f"{DIM}{evolves}{RESET}"])
    out = [f"{ESC}[H{ESC}[2J"] + [f"{ESC}[{i + 1};1H{l}" for i, l in enumerate(lines)]
    for i, col in enumerate(cols):
        for j, l in enumerate(col):
            out.append(f"{ESC}[{len(lines) + j + 1};{2 + i * SLOT}H{l}")
    blurb = STARTER_BLURBS[list(STARTERS)[pos]]
    out.append(f"{ESC}[{len(lines) + len(cols[0]) + 2};1H{blurb}")
    sys.stdout.write("".join(out))
    sys.stdout.flush()


def choose():
    """Interactive picker. Returns the chosen starter line, or None."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    pos, breath, chosen = 0, False, None
    sys.stdout.write(f"{ESC}[?1049h{ESC}[?25l")
    try:
        tty.setcbreak(fd)
        while True:
            draw(pos, breath)
            ready, _, _ = select.select([fd], [], [], 1.5)
            if not ready:
                breath = not breath
                continue
            key = os.read(fd, 8).decode(errors="ignore")
            if key in ("\r", "\n"):
                chosen = list(STARTERS)[pos]
                break
            if key in ("q", "\x1b"):
                break
            pos = (pos + KEYS.get(key, 0)) % len(STARTERS)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write(f"{ESC}[?25h{ESC}[?1049l")
        sys.stdout.flush()
    return chosen


def main():
    """Exit code 0 when a starter is (or already was) chosen."""
    s = state.load()
    if s["starter"]:
        print(f"  Your starter is {FORM_NAMES[STARTERS[s['starter']][0]]}'s line. `bashou reset` to start over.")
        return 0
    if not sys.stdin.isatty():
        return 1
    line = choose()
    if not line:
        print(f"  {DIM}No starter yet. Run `bashou start` when you're ready.{RESET}")
        return 1
    with state.locked() as s:
        s["starter"], s["active"] = line, "starter"
    print(f"  {BOLD}{FORM_NAMES[STARTERS[line][0]]}{RESET} is your starter! It levels up every 5 achievements.")
    return 0
