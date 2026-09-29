"""Security investigations, picked by you, easy to hard, with no clock: one of `bashou arena`'s two
choices (`bashou arena security`; the old `bashou security` still leads there)."""

from . import challenges, fight, progress, state
from .i18n import _
from .render import BOLD, DIM, RESET, GOOD

LEVELS = {1: "easy", 2: "medium", 3: "hard"}


def listing():
    done = set(state.load()["security"])
    print(f"  {BOLD}" + _("Security challenges") + f"{RESET} {DIM}· "
          + _("{n} solved").format(n=f"{len(done)}/{len(challenges.SECURITY)}") + RESET + "\n")
    for i, ch in enumerate(challenges.SECURITY, 1):
        mark = f"{GOOD}✓{RESET}" if ch.id in done else " "
        missing = "" if ch.available() else f"  {DIM}(" + _("needs {tools}").format(tools=", ".join(ch.requires)) + f"){RESET}"
        print(f"  {mark} {i}. {_(ch.threat):<16} {DIM}{_(LEVELS[ch.level])}{RESET}{missing}")
    print(f"\n  {DIM}" + _("Start one: bashou arena security <number>") + RESET)
    print(f"  {DIM}" + _("Ideas for more? Open an issue on GitHub.") + RESET)


def find(key):
    if key.isdigit() and 1 <= int(key) <= len(challenges.SECURITY):
        return challenges.SECURITY[int(key) - 1]
    ch = challenges.BY_ID.get(key)
    return ch if ch and ch.kind == "security" else None


def intro(ch, task):
    return (f"\n{BOLD}🔍 " + _("Security challenge: {title}").format(title=_(ch.threat)) + f"{RESET} "
            f"{DIM}({_(LEVELS[ch.level])}){RESET}\n\n{task}\n\n"
            f"{DIM}" + _("You're in a sandbox folder with a real bash. Commands:") + f"{RESET}\n"
            "  answer <value>   " + _("check your answer") + "\n"
            "  hint             " + _("get a hint") + "\n"
            "  task             " + _("show the task again") + "\n"
            "  flee             " + _("give up (try again any time)") + "\n")


def choose(key):
    """The challenge `key` names (number or id), or None after saying why not."""
    ch = find(key)
    if not ch:
        print("  " + _("No such challenge: {key}. `bashou arena security` lists them.").format(key=key))
        return None
    if not ch.available():
        print("  " + _("This one needs {tools}, which isn't installed.").format(tools=", ".join(ch.requires)))
        return None
    return ch


def play(ch):
    """One investigation in the arena. True when solved."""
    code, notes = fight.arena(ch, lambda task: intro(ch, task))
    won = code == fight.WIN
    if won:
        with state.locked() as s:
            if ch.id not in s["security"]:
                s["security"].append(ch.id)
            notes += progress.check(s)
        print(f"\n{GOOD}{BOLD}✨ " + _("Solved: {title}!").format(title=_(ch.threat)) + RESET)
    for note in notes:
        print(f"  {note}")
    print()
    return won
