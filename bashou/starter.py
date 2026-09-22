"""First launch: pick a language, then your starter (once: only `bashou reset` lets you pick again)."""

import os
import select
import sys
import termios
import tty

from . import creatures, render, state
from . import i18n
from .creatures import FORM_NAMES, STARTER_BLURBS, STARTERS
from .i18n import _

ESC = "\x1b"
BOLD, DIM, RESET, REV = f"{ESC}[1m", f"{ESC}[2m", f"{ESC}[0m", f"{ESC}[7m"
KEYS = {"\x1b[C": 1, "l": 1, "\x1b[D": -1, "h": -1}
SLOT = 26


def draw(pos, breath):
    lines = [f"{BOLD}{_('Choose your starter')}{RESET}  "
             f"{DIM}{_('(for good: only `bashou reset` lets you choose again)')}{RESET}",
             "", f"{DIM}{_('←/→ to look, Enter to choose, q to decide later')}{RESET}", ""]
    cols = []
    for i, line in enumerate(STARTERS):
        forms = STARTERS[line]
        pet = creatures.get(forms[0])
        cells = [[True] * pet.width for _ in range(len(pet.base) // 2)]
        sprite = render.lines(pet, ["inhale"] if breath and i == pos else [], cells)
        name = _(FORM_NAMES[forms[0]])
        title = f"{REV} {name} {RESET}" if i == pos else f" {name} "
        evolves = " → ".join([name] + ["?"] * (len(forms) - 1))                # to discover
        cols.append(sprite + ["", title, f"{DIM}{evolves}{RESET}"])
    out = [f"{ESC}[H{ESC}[2J"] + [f"{ESC}[{i + 1};1H{l}" for i, l in enumerate(lines)]
    for i, col in enumerate(cols):
        for j, l in enumerate(col):
            out.append(f"{ESC}[{len(lines) + j + 1};{2 + i * SLOT}H{l}")
    blurb = _(STARTER_BLURBS[list(STARTERS)[pos]])
    out.append(f"{ESC}[{len(lines) + len(cols[0]) + 2};1H{blurb}")
    sys.stdout.write("".join(out))
    sys.stdout.flush()


def pick(draw, count, keys=KEYS, start=0):
    """Full-screen picker: draw(pos, breath) until Enter (returns pos) or q (returns None)."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    pos, breath, chosen = start, False, None
    sys.stdout.write(f"{ESC}[?1049h{ESC}[?25l")
    try:
        tty.setcbreak(fd)
        while True:
            draw(pos, breath)
            if not select.select([fd], [], [], 1.5)[0]:
                breath = not breath
                continue
            key = os.read(fd, 8).decode(errors="ignore")
            if key in ("\r", "\n"):
                chosen = pos
                break
            if key in ("q", "\x1b", "\x04", "\x03"):   # also Ctrl+D, Ctrl+C
                break
            pos = (pos + keys.get(key, 0)) % count
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write(f"{ESC}[?25h{ESC}[?1049l")
        sys.stdout.flush()
    return chosen


def choose():
    """Starter picker. Returns the chosen starter line, or None."""
    pos = pick(draw, len(STARTERS))
    return None if pos is None else list(STARTERS)[pos]


LANG_KEYS = {"\x1b[B": 1, "j": 1, "\x1b[A": -1, "k": -1}


def draw_languages(pos, breath):
    """Always in English plus each language's own name, since we don't know yet what you read."""
    out = [f"{ESC}[H{ESC}[2J", f"{BOLD}Language{RESET}  {DIM}↑/↓, Enter · `bashou language` to change it later{RESET}\n\n"]
    for i, (code, name) in enumerate(i18n.LANGUAGES.items()):
        done, total = i18n.progress_of(code) if code != "en" else (1, 1)
        note = "" if done == total else f"  {DIM}({100 * done // total}% translated, the rest in English){RESET}"
        label = f"{REV} {name} {RESET}" if i == pos else f" {name} "
        out.append(f"  {label}{note}\n")
    sys.stdout.write("".join(out))
    sys.stdout.flush()


def choose_language():
    codes = list(i18n.LANGUAGES)
    current = state.load().get("language") or "en"
    pos = pick(draw_languages, len(codes), LANG_KEYS, codes.index(current) if current in codes else 0)
    return None if pos is None else codes[pos]


def language_main():
    """`bashou language`. Exit code 0 when a language is (or already was) set."""
    if not sys.stdin.isatty():
        return 0 if state.load().get("language") else 1
    lang = choose_language() or state.load().get("language") or "en"     # q: keep it, or English
    with state.locked() as s:
        s["language"] = lang
    i18n.use(lang)
    print("  " + _("Language: {name}").format(name=i18n.LANGUAGES[lang]))
    return 0


def main():
    """Exit code 0 when a starter is (or already was) chosen."""
    s = state.load()
    if not s.get("language") and sys.stdin.isatty():
        language_main()
    if s["starter"]:
        print("  " + _("Your starter is {name}'s line. `bashou reset` to start over.").format(
            name=_(FORM_NAMES[STARTERS[s["starter"]][0]])))
        return 0
    if not sys.stdin.isatty():
        return 1
    line = choose()
    if not line:
        print(f"  {DIM}" + _("No starter yet. Run `bashou start` when you're ready.") + RESET)
        return 1
    with state.locked() as s:
        s["starter"], s["active"] = line, "starter"
    print("  " + _("{name} is your starter! It levels up every 5 achievements.").format(
        name=f"{BOLD}{_(FORM_NAMES[STARTERS[line][0]])}{RESET}"))
    return 0
