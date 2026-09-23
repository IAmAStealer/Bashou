"""What you want to learn (owner, 2026-09-23): a bit of everything, or the skills you tick.

Asked once before the starter (`bashou start`), changed any time with `bashou skills`. Fights and the
adventure's paths only come from those skills; fights you already won still come back for review.
"""

import shutil
import sys

from . import state
from .challenges import family
from .i18n import _

ESC = "\x1b"
BOLD, DIM, RESET, REV = f"{ESC}[1m", f"{ESC}[2m", f"{ESC}[0m", f"{ESC}[7m"

# skill -> what it covers, in the order of the list (the adventure's topics, world.TOPICS)
SKILLS = {
    "bash": "Bash: grep, sed, awk, find, pipes",
    "linux": "Linux: files, users, permissions, processes",
    "systemd": "systemd: services, timers, logs",
    "debian": "Debian and Ubuntu: apt, dpkg, repositories",
    "rocky": "Rocky and Red Hat: dnf, rpm, repositories",
    "python": "Python: small scripts to fix",
    "c": "C: compiling, memory, pointers",
    "rust": "Rust: variables, types, the compiler",
    "logic": "Logic: coding basics, for beginners",
    "cicd": "CI/CD: pipelines, secrets, runners",
}
# Fights need a program or a system: without it, the skill still has its adventure questions.
NEEDS = {"python": "python3", "c": "gcc", "rust": "rustc"}
SYSTEMS = {"debian": {"debian"}, "rocky": {"rhel", "fedora", "centos"}}


def picked(s):
    """The skills you learn: every one, or those you ticked."""
    return list(SKILLS) if s.get("skills", "all") == "all" else [k for k in SKILLS if k in s["skills"]]


def wanted(s, skill):
    return s.get("skills", "all") == "all" or skill in s["skills"]


def note(skill):
    """Why this skill has no fights here, or ""."""
    if skill in NEEDS and not shutil.which(NEEDS[skill]):
        return _("no {program} here: questions only").format(program=NEEDS[skill])
    if skill in SYSTEMS and not SYSTEMS[skill] & family():
        return _("another system: questions only")
    return ""


def draw_mode(pos, breath):
    out = [f"{ESC}[H{ESC}[2J", f"{BOLD}{_('What do you want to learn?')}{RESET}  "
           f"{DIM}{_('↑/↓, Enter · `bashou skills` to change it later')}{RESET}\n\n"]
    for i, label in enumerate((_("A bit of everything (all skills)"), _("Pick my skills"))):
        out.append(f"  {REV} {label} {RESET}\n" if i == pos else f"   {label}\n")
    sys.stdout.write("".join(out))
    sys.stdout.flush()


def checklist_drawer(ticked):
    def draw(pos, breath):
        out = [f"{ESC}[H{ESC}[2J", f"{BOLD}{_('Pick your skills')}{RESET}  "
               f"{DIM}{_('↑/↓ to move, Space to tick, Enter when done')}{RESET}\n\n"]
        for i, skill in enumerate(SKILLS):
            box = "[x]" if skill in ticked else "[ ]"
            text = f"{box} {_(SKILLS[skill])}"
            line = f"  {REV} {text} {RESET}" if i == pos else f"   {text} "
            why = note(skill)
            out.append(line + (f"  {DIM}({why}){RESET}" if why else "") + "\n")
        if not ticked:
            out.append(f"\n  {DIM}{_('Tick at least one.')}{RESET}\n")
        sys.stdout.write("".join(out))
        sys.stdout.flush()
    return draw


def choose(current="all"):
    """"all", a list of skills, or None (q)."""
    from .starter import LANG_KEYS, pick
    mode = pick(draw_mode, 2, LANG_KEYS, 0 if current == "all" else 1)
    if mode is None:
        return None
    if mode == 0:
        return "all"
    ticked = set(SKILLS if current == "all" else current)
    keys = list(SKILLS)
    while True:
        pos = pick(checklist_drawer(ticked), len(keys), LANG_KEYS,
                   toggle=lambda p: ticked.symmetric_difference_update({keys[p]}))
        if pos is None:
            return None
        if ticked:
            return "all" if len(ticked) == len(keys) else [k for k in keys if k in ticked]


def ask(current="all"):
    """Ask and save. q keeps what was there."""
    choice = choose(current)
    if choice is None:
        return current
    with state.locked() as s:
        s["skills"] = choice
    return choice


def show(choice):
    if choice == "all":
        print("  " + _("You learn a bit of everything."))
    else:
        print("  " + _("You learn: {skills}").format(skills=", ".join(_(SKILLS[k]).split(":")[0].strip() for k in choice)))


def main():
    """`bashou skills`."""
    current = state.load().get("skills", "all")
    if not sys.stdin.isatty():
        show(current)
        return 0
    show(ask(current))
    return 0
