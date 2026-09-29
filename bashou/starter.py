"""First launch: pick a language, then your starter (once: only `bashou reset` lets you pick again)."""

import sys

from . import creatures, render, state, terminal
from . import i18n
from .creatures import FAMILIES, PETS, STARTERS
from .i18n import _
from .render import ESC, BOLD, DIM, RESET, REV

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
        name = _(PETS[forms[0]].name)
        title = f"{REV} {name} {RESET}" if i == pos else f" {name} "
        cols.append(sprite + ["", title])
    out = [f"{ESC}[H{ESC}[2J"] + [f"{ESC}[{i + 1};1H{l}" for i, l in enumerate(lines)]
    for i, col in enumerate(cols):
        for j, l in enumerate(col):
            out.append(f"{ESC}[{len(lines) + j + 1};{2 + i * SLOT}H{l}")
    blurb = _(FAMILIES[list(STARTERS)[pos]].blurb)
    out.append(f"{ESC}[{len(lines) + len(cols[0]) + 2};1H{blurb}")
    sys.stdout.write("".join(out))
    sys.stdout.flush()


def pick(draw, count, keys=KEYS, start=0, toggle=None):
    """Full-screen picker: draw(pos, breath) until Enter (returns pos) or q (returns None).
    With `toggle`, Space calls toggle(pos) (a checklist)."""
    pos, breath = start, False
    with terminal.Screen(wrap=True) as screen:
        while True:
            draw(pos, breath)
            pressed = screen.keys(1.5)
            if not pressed:
                breath = not breath
            for key in pressed:
                what = terminal.name(key)
                if what == "enter":
                    return pos
                if what == "quit":
                    return None
                if key == " " and toggle:
                    toggle(pos)
                pos = (pos + keys.get(key, 0)) % count


def choose():
    """Starter picker. Returns the chosen starter line, or None."""
    pos = pick(draw, len(STARTERS))
    return None if pos is None else list(STARTERS)[pos]


LANG_KEYS = {"\x1b[B": 1, "j": 1, "\x1b[A": -1, "k": -1}


def draw_languages(pos, breath):
    """Always in English plus each language's own name, since we don't know yet what you read."""
    out = [f"{ESC}[H{ESC}[2J", f"{BOLD}Language{RESET}  {DIM}↑/↓, Enter · `bashou config language` to change it later{RESET}\n\n"]
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
    """`bashou config language`. Exit code 0 when a language is (or already was) set."""
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
            name=_(PETS[STARTERS[s["starter"]][0]].name)))
        return 0
    if not sys.stdin.isatty():
        return 1
    from . import skills
    skills.show(skills.ask(s.get("skills", "all")))
    line = choose()
    if not line:
        print(f"  {DIM}" + _("No starter yet. Run `bashou start` when you're ready.") + RESET)
        return 1
    with state.locked() as s:
        s["starter"], s["active"] = line, "starter"
    print("  " + _("{name} is your starter! It levels up every 5 achievements.").format(
        name=f"{BOLD}{_(PETS[STARTERS[line][0]].name)}{RESET}"))
    return 0
