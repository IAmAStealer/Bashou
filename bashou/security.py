"""`bashou security`: small security investigations, picked by you, easy to hard."""

from . import challenges, fight, progress, state
from .i18n import _

BOLD, DIM, RESET, GOOD = "\033[1m", "\033[2m", "\033[0m", "\033[38;2;130;210;130m"
LEVELS = {1: "easy", 2: "medium", 3: "hard"}


def listing():
    done = set(state.load()["security"])
    print(f"  {BOLD}" + _("Security challenges") + f"{RESET} {DIM}· "
          + _("{n} solved").format(n=f"{len(done)}/{len(challenges.SECURITY)}") + RESET + "\n")
    for i, ch in enumerate(challenges.SECURITY, 1):
        mark = f"{GOOD}✓{RESET}" if ch.id in done else " "
        missing = "" if ch.available() else f"  {DIM}(" + _("needs {tools}").format(tools=", ".join(ch.requires)) + f"){RESET}"
        print(f"  {mark} {i}. {_(ch.threat):<16} {DIM}{_(LEVELS[ch.level])}{RESET}{missing}")
    print(f"\n  {DIM}" + _("Start one: bashou security <number>") + RESET)
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


def run(key):
    if not key:
        listing()
        return 0
    ch = find(key)
    if not ch:
        print("  " + _("No such challenge: {key}. `bashou security` lists them.").format(key=key))
        return 1
    if not ch.available():
        print("  " + _("This one needs {tools}, which isn't installed.").format(tools=", ".join(ch.requires)))
        return 1
    won, notes = fight.arena(ch, lambda task: intro(ch, task))
    if won:
        with state.locked() as s:
            if ch.id not in s["security"]:
                s["security"].append(ch.id)
            notes += progress.check(s)
        print(f"\n{GOOD}{BOLD}✨ " + _("Solved: {title}!").format(title=_(ch.threat)) + RESET)
    else:
        print(f"\n{DIM}" + _("No worries, try again any time: bashou security {n}").format(
            n=challenges.SECURITY.index(ch) + 1) + RESET)
    for note in notes:
        print(f"  {note}")
    print()
    return 0
