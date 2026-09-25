"""`bashou lesson`: the Sage Owl's library (owner, 2026-09-25).

Hints say what to type; a lesson shows how things work, page by page, with a picture (a scheme) that
grows from one page to the next and the owl pointing at the part that matters. Lessons unlock as you
play, each one preparing the next step: the stack and the heap before the C memory fights, and so on.

Lessons are JSON files (see doc/contributing/lessons.md): en/<id>.json holds the lesson, its skill and
what unlocks it; <lang>/<id>.json only translates title, summary and pages (English fills the gaps).
"""

import json
from pathlib import Path

from .. import achievements, challenges, i18n, skills, state
from ..i18n import _

HERE = Path(__file__).resolve().parent
SCHEME_WIDTH = 50               # the owl stands to the right of the scheme: 50 + owl fits 80 columns
SCHEME_LINES = 14
TEXT_LINES = 9
TEXT_WIDTH = 72


def load(lang=None):
    """Every lesson, in order, translated into `lang` where a translation exists."""
    lang = lang or i18n.language()
    found = []
    for path in sorted((HERE / "en").glob("*.json")):
        lesson = json.loads(path.read_text())
        local = HERE / lang / path.name
        if lang != "en" and local.exists():
            lesson.update({k: v for k, v in json.loads(local.read_text()).items()
                           if k in ("title", "summary", "pages")})
        found.append(lesson)
    return sorted(found, key=lambda le: le["order"])


def progress_of(s):
    """s["lessons"], with every field (a save from an older version may lack some)."""
    p = s.setdefault("lessons", {})
    for key, empty in (("read", []), ("opened", []), ("page", {})):
        p.setdefault(key, empty)
    return p


def read(s):
    return (s.get("lessons") or {}).get("read", [])


def met(s, cond):
    """Is one condition true? "lesson ID", "commands N", "tool NAME N", "won ID", "fights N",
    "achievement ID"."""
    kind, *args = cond.split()
    if kind == "lesson":
        return args[0] in read(s)
    if kind == "commands":
        return s["commands"] >= int(args[0])
    if kind == "tool":
        return s["tools"].get(args[0], 0) >= int(args[1])
    if kind == "won":
        return args[0] in s["challenges"]
    if kind == "fights":
        return s["fights_won"] >= int(args[0])
    if kind == "achievement":
        return args[0] in s["achievements"]
    raise ValueError(cond)


def unlocked(s, lesson):
    """Every entry of "needs" holds; an entry "a | b" holds when one of its sides does."""
    return all(any(met(s, c.strip()) for c in need.split("|")) for need in lesson.get("needs", []))


def describe(cond, titles, s=None):
    """A condition in words for the list: "beat the Semicolon slug", "run 50 commands (32/50)"."""
    kind, *args = cond.split()
    if kind == "lesson":
        return _("read “{title}”").format(title=titles.get(args[0], args[0]))
    if kind == "commands":
        text = _("run {n} commands").format(n=args[0])
        return text + (f" ({s['commands']}/{args[0]})" if s else "")
    if kind == "tool":
        text = (_("use {tool} once") if args[1] == "1" else _("use {tool} {n} times")).format(tool=args[0], n=args[1])
        return text + (f" ({s['tools'].get(args[0], 0)}/{args[1]})" if s else "")
    if kind == "won":
        ch = challenges.BY_ID.get(args[0])
        return _("beat the {threat} in a fight").format(threat=_(ch.threat) if ch else args[0])
    if kind == "fights":
        text = _("win {n} fights").format(n=args[0])
        return text + (f" ({s['fights_won']}/{args[0]})" if s else "")
    if kind == "achievement":
        a = next((a for a in achievements.ALL if a.id == args[0]), None)
        return _("earn the achievement “{name}”").format(name=_(a.name) if a else args[0])
    return cond


def how_to_unlock(s, lesson, titles):
    """What is still missing, e.g. "read “Pipes” · beat the Semicolon slug in a fight"."""
    missing = []
    for need in lesson.get("needs", []):
        sides = [c.strip() for c in need.split("|")]
        if not any(met(s, c) for c in sides):
            missing.append(_(" or ").join(describe(c, titles, s) for c in sides))
    return " · ".join(missing)


def shown(s, lessons):
    """The lessons of the skills you learn (lessons with no skill are for everyone). A lesson you
    already opened stays, even if you untick its skill later."""
    opened = (s.get("lessons") or {}).get("opened", [])
    return [le for le in lessons if not le.get("skill") or skills.wanted(s, le["skill"]) or le["id"] in opened]


def new(s, lessons=None):
    """Unlocked lessons you haven't opened yet (the pets mention them, `bashou level` too)."""
    lessons = shown(s, lessons if lessons is not None else load("en"))
    opened = (s.get("lessons") or {}).get("opened", [])
    return [le for le in lessons if le["id"] not in opened and unlocked(s, le)]


def main(args):
    import sys
    lessons = load()
    s = state.load()
    if args and args[0] == "list" or not sys.stdin.isatty():
        return print_list(s, lessons)
    from . import reader
    return reader.run(lessons, args[0] if args else None)


def print_list(s, lessons):
    """`bashou lesson list` (or outside a terminal): the library as text."""
    titles = {le["id"]: le["title"] for le in lessons}
    for le in shown(s, lessons):
        if le["id"] in read(s):
            print(f"  ✔ {le['title']}")
        elif unlocked(s, le):
            print(f"  📖 {le['title']}  \x1b[2m{le['summary']}\x1b[0m")
        else:
            print(f"  \x1b[2m🔒 {le['title']} · {how_to_unlock(s, le, titles)}\x1b[0m")
    return 0
