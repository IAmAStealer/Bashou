"""First launch: pick a language, what you want to learn, then your starter (once: only `bashou reset` lets
you pick again). The same pickers serve `bashou config language` and `bashou config skills`."""

import os
import sys

from . import creatures, render, skills, state, terminal
from . import i18n
from .creatures import FAMILIES, PETS, STARTERS
from .i18n import _
from .render import ESC, BOLD, DIM, RESET, REV

KEYS = {"\x1b[C": 1, "l": 1, "\x1b[D": -1, "h": -1}
SLOT = 26


def draw(pos, breath):
    width = render.columns()
    slot = max(18, min(SLOT, (width - 2) // len(STARTERS)))     # a portrait terminal: closer together
    lines = render.heading(_("Choose your starter"), _("(for good: only `bashou reset` lets you choose again)"), width)
    lines += ["", f"{DIM}{_('←/→ to look, Enter to choose, q to decide later')}{RESET}", ""]
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
            out.append(f"{ESC}[{len(lines) + j + 1};{2 + i * slot}H{l}")
    blurb = render.wrap(_(FAMILIES[list(STARTERS)[pos]].blurb), width - 1, 4)
    out += [f"{ESC}[{len(lines) + len(cols[0]) + 2 + k};1H{line}" for k, line in enumerate(blurb)]
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
    out = [f"{ESC}[H{ESC}[2J"] + [line + "\n" for line in render.heading(
        "Language", "↑/↓, Enter · `bashou config language` to change it later", render.columns())] + ["\n"]
    for i, (code, name) in enumerate(i18n.LANGUAGES.items()):
        done, total = i18n.progress_of(code) if code != "en" else (1, 1)
        note = "" if done == total else f"({100 * done // total}% translated, the rest in English)"
        label = f"{REV} {name} {RESET}" if i == pos else f" {name} "
        out += [line + "\n" for line in render.beside(f"  {label}", note, render.columns())]
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
    show_skills(ask_skills(s.get("skills", "all")))
    ask_editor()
    line = choose()
    if not line:
        if os.environ.get("BASHOU_AUTO"):           # opened by the package's loader: it won't open again by itself
            print(f"  {DIM}" + _("No starter yet, so Bashou stays off. Run `bashou on` when you want to meet your pet.") + RESET)
        else:
            print(f"  {DIM}" + _("No starter yet. Run `bashou start` when you're ready.") + RESET)
        return 1
    with state.locked() as s:
        s["starter"], s["active"] = line, "starter"
    print("  " + _("{name} is your starter! It levels up every 5 achievements.").format(
        name=f"{BOLD}{_(PETS[STARTERS[line][0]].name)}{RESET}"))
    return 0


# --- the editor your hints show (owner: editing a file comes at the start) -------------------------

EDITORS = ("nano", "vi")


def draw_editor(pos, breath):
    out = [f"{ESC}[H{ESC}[2J"] + [line + "\n" for line in render.heading(
        _("Which editor do you want to learn?"), _("↑/↓, Enter · `bashou config editor` to change it later"),
        render.columns())] + ["\n"]
    labels = (_("nano: simple, what you type goes into the file (a good start)"),
              _("vi: two modes, on every system, even the smallest"))
    for i, label in enumerate(labels):
        for k, part in enumerate(render.wrap(label, render.columns() - 6, 3)):
            out.append(f"  {REV} {part} {RESET}\n" if i == pos else f"   {part}\n")
    sys.stdout.write("".join(out))
    sys.stdout.flush()


def ask_editor():
    """Ask and save the editor setting. q keeps what was there."""
    current = state.setting(state.load(), "editor")
    pos = pick(draw_editor, len(EDITORS), LANG_KEYS, EDITORS.index(current) if current in EDITORS else 0)
    if pos is not None:
        with state.locked() as s:
            s.setdefault("settings", {})["editor"] = EDITORS[pos]


# --- what you want to learn (bashou/skills.py) --------------------------------------------------

def draw_mode(pos, breath):
    out = [f"{ESC}[H{ESC}[2J"] + [line + "\n" for line in render.heading(
        _("What do you want to learn?"), _("↑/↓, Enter · `bashou config skills` to change it later"), render.columns())] + ["\n"]
    for i, label in enumerate((_("A bit of everything (all skills)"), _("Pick my skills"))):
        out.append(f"  {REV} {label} {RESET}\n" if i == pos else f"   {label}\n")
    sys.stdout.write("".join(out))
    sys.stdout.flush()


def checklist_drawer(ticked):
    def draw(pos, breath):
        width = render.columns()
        out = [f"{ESC}[H{ESC}[2J"] + [line + "\n" for line in render.heading(
            _("Pick your skills"), _("↑/↓ to move, Space to tick, Enter when done"), width)] + ["\n"]
        for i, skill in enumerate(skills.SKILLS):
            box = "[x]" if skill in ticked else "[ ]"
            text = f"{box} {_(skills.SKILLS[skill].text)}"
            line = f"  {REV} {text} {RESET}" if i == pos else f"   {text} "
            why = skills.note(skill)
            out += [part + "\n" for part in render.beside(line, f"({why})" if why else "", width, 7)]
        if not ticked:
            out.append(f"\n  {DIM}{_('Tick at least one.')}{RESET}\n")
        sys.stdout.write("".join(out))
        sys.stdout.flush()
    return draw


def choose_skills(current="all"):
    """"all", a list of skills, or None (q)."""
    mode = pick(draw_mode, 2, LANG_KEYS, 0 if current == "all" else 1)
    if mode is None:
        return None
    if mode == 0:
        return "all"
    ticked = set(skills.SKILLS if current == "all" else current)
    keys = list(skills.SKILLS)
    while True:
        pos = pick(checklist_drawer(ticked), len(keys), LANG_KEYS,
                   toggle=lambda p: ticked.symmetric_difference_update({keys[p]}))
        if pos is None:
            return None
        if ticked:
            return "all" if len(ticked) == len(keys) else [k for k in keys if k in ticked]


def ask_skills(current="all"):
    """Ask and save. q keeps what was there."""
    choice = choose_skills(current)
    if choice is None:
        return current
    with state.locked() as s:
        s["skills"] = choice
    return choice


def show_skills(choice):
    if choice == "all":
        print("  " + _("You learn a bit of everything."))
    else:
        print("  " + _("You learn: {skills}").format(skills=", ".join(_(skills.SKILLS[k].text).split(":")[0].strip() for k in choice)))


def skills_main():
    """`bashou config skills`."""
    current = state.load().get("skills", "all")
    if not sys.stdin.isatty():
        show_skills(current)
        return 0
    show_skills(ask_skills(current))
    return 0
