"""`bashou project`: the command (the projects themselves, and what they count, are in __init__)."""

import shutil
import textwrap
from datetime import date

from .. import skills, state
from ..i18n import _
from ..render import BOLD, DIM, RESET
from . import LANGUAGES, load, progress_of

GREEN = "\033[38;2;120;200;120m"


def find(words, projects):
    """The project named by `words`: "python photos", "python_photos" or "photos" when only one has it."""
    key = "_".join(w.lower() for w in words)
    for p in projects:
        if key == p["id"]:
            return p
    named = [p for p in projects if p["name"] == key]
    return named[0] if len(named) == 1 else None


def width():
    return max(40, min(100, shutil.get_terminal_size((80, 24)).columns) - 4)


def say(text, indent="  ", style=""):
    for para in text.split("\n"):
        for line in textwrap.wrap(para, width() - len(indent)) or [""]:
            print(indent + style + line + (RESET if style else ""))


def level_name(p):
    return _(p["difficulty"])


def show_step(p, number):
    """Step `number` (from 0) of project `p`: what to do, and when it's done."""
    step = p["steps"][number]
    print(f"  {BOLD}" + _("Step {n}/{total}").format(n=number + 1, total=len(p["steps"])) + f"{RESET} · {p['title']}")
    say(step["do"], "    ")
    say(_("Done when: {done}").format(done=step["done"]), "    ", DIM)


def overview(s, projects):
    p = progress_of(s)
    done = p["done"]
    by_id = {pr["id"]: pr for pr in projects}
    current = by_id.get(p["current"])
    if current and done.get(current["id"], 0) < len(current["steps"]):
        show_step(current, done.get(current["id"], 0))
        print("    " + DIM + _("Done? bashou project next · Stuck? bashou project hint") + RESET)
        print()
    elif not p["current"]:
        say(_("Real programs to build, one small step at a time. Each step says what to do and when it's done, "
              "not how: searching is part of learning. Pick one that you would really use."))
        print()
    from .. import lesson
    read = set((s.get("lessons") or {}).get("read", []))
    titles = {le["id"]: le["title"] for le in lesson.load()}
    for lang, (label, skill) in LANGUAGES.items():
        mine = [pr for pr in projects if pr["language"] == lang]
        if not mine or not (skills.wanted(s, skill) or any(pr["id"] in done for pr in mine)):
            continue
        print(f"  {BOLD}{label}{RESET}")
        for pr in mine:
            n, total = min(done.get(pr["id"], 0), len(pr["steps"])), len(pr["steps"])
            mark = f"{GREEN}✔{RESET}" if n >= total else ("▶" if pr["id"] == p["current"] else " ")
            count = f"{n}/{total}" if n else ""
            print(f"   {mark} {pr['name']:<9} {pr['title']} {DIM}· {level_name(pr)}{RESET} {count}")
            unread = [titles[le] for le in pr.get("lessons", []) if le in titles and le not in read]
            if unread and n < total:                # one lesson, the next one to read: not a reading list
                say("🦉 " + _("A lesson that helps: {title}").format(title=unread[0]), "       ", DIM)
    print()
    print("  " + DIM + _("Start one: bashou project start python photos") + RESET)


def start(s, p):
    prog = progress_of(s)
    prog["current"] = p["id"]
    n = prog["done"].get(p["id"], 0)
    if n >= len(p["steps"]):
        print("  " + _("You already finished {title}. Its steps stay here to read again:").format(title=p["title"]))
        n = len(p["steps"]) - 1
    else:
        say(p["pitch"])
        print()
        if n:
            print("  " + _("Welcome back: you stopped here."))
    show_step(p, n)


def step_forward(s, p):
    """`next`: the current step is done. What it taught, then the next step (or the end)."""
    prog = progress_of(s)
    n = prog["done"].get(p["id"], 0)
    if n >= len(p["steps"]):
        print("  " + _("{title} is finished. Pick another one: bashou project").format(title=p["title"]))
        return
    prog["done"][p["id"]] = n + 1
    today = date.today().isoformat()
    if today not in prog["days"]:
        prog["days"].append(today)
        prog["days"] = prog["days"][-60:]
    print(f"  {GREEN}✔{RESET} " + _("Step {n} done.").format(n=n + 1))
    say(p["steps"][n]["why"], "    ")
    print()
    if n + 1 < len(p["steps"]):
        show_step(p, n + 1)
    else:
        say("🏁 " + _("{title}: finished! You built a real program, one small step at a time. Use it, show it, and "
                     "change it when you need more: that's what programmers do every day.").format(title=p["title"]))
        prog["current"] = ""
        print("  " + DIM + _("Another one? bashou project") + RESET)


def step_back(s, p):
    prog = progress_of(s)
    n = prog["done"].get(p["id"], 0)
    if not n:
        print("  " + _("You're on the first step already."))
        return
    prog["done"][p["id"]] = n - 1
    prog["current"] = p["id"]
    print("  " + _("Back one step: it's not done yet."))
    show_step(p, n - 1)


def main(words):
    words = list(words or [])
    action = words.pop(0).lower() if words else ""
    projects = load()
    with state.locked() as s:
        prog = progress_of(s)
        current = next((p for p in projects if p["id"] == prog["current"]), None)
        if action in ("", "list"):
            overview(s, projects)
        elif action == "start":
            p = find(words, projects)
            if not p:
                print("  " + _("Which project? For example: bashou project start python photos"))
                overview(s, projects)
                return 1
            start(s, p)
        elif action in ("next", "hint", "back"):
            if not current:
                print("  " + _("No project started yet. Pick one: bashou project start python photos"))
                return 1
            if action == "next":
                step_forward(s, current)
            elif action == "back":
                step_back(s, current)
            else:
                n = min(prog["done"].get(current["id"], 0), len(current["steps"]) - 1)
                print("  💡 " + _("Hint for step {n}:").format(n=n + 1))
                say(current["steps"][n]["hint"], "    ")
        else:
            print("  " + _("bashou project [start <language> <project> | next | hint | back]"))
            return 1
    return 0
