"""The library screen of `bashou lesson`: the list of lessons, then a lesson page by page.

A page is a scheme (a small drawing in text) with the owl beside it, its wing pointing at the line that
matters, and a few short lines of text below. Words listed in "mark" stand out in the scheme: that's
usually what changed since the previous page.
"""

import os
import random
import select
import sys
import termios
import tty

from .. import creatures, render, skills, state
from ..i18n import _
from . import HERE, how_to_unlock, progress_of, read, shown, unlocked

ESC = "\x1b"
DIM, BOLD, RESET, REV = f"{ESC}[2m", f"{ESC}[1m", f"{ESC}[0m", f"{ESC}[7m"
ACCENT = f"{ESC}[38;2;240;200;110m"
CMD = f"{ESC}[38;2;130;210;120m"
TITLE = f"{ESC}[38;2;150;190;230m"
LEADER = f"{ESC}[38;2;122;86;52m"            # the owl's outline brown: the dotted line is its gesture
KEYS = {"\x1b[A": "up", "\x1b[B": "down", "\x1b[C": "right", "\x1b[D": "left",
        "k": "up", "j": "down", "l": "right", "h": "left", "\r": "enter", "\n": "enter", " ": "right",
        "q": "quit", "\x1b": "quit", "\x04": "quit", "\x03": "quit"}
OWL = creatures.load(HERE / "owl.json")
WING = 3                      # terminal line of the owl's wing tip (its first column)
TOP = 3                       # first line of a scheme, under the title and a blank line
LEFT = 4                      # first column of the scheme and of the text


def owl_top(lesson):
    """How far down the scheme starts in this lesson, so the owl's head fits above its highest point.
    The same for every page: a scheme that grows mustn't jump."""
    points = [p["point"] for p in lesson["pages"] if p.get("point") is not None]
    return TOP + max(0, WING - 1 - min(points, default=WING))


def owl_col(lesson):
    """The owl's column: right of the widest scheme of the lesson, so it stays put from page to page."""
    return LEFT + max((render.width(line) for p in lesson["pages"] for line in p.get("scheme", [])), default=0) + 3


def paint(line, marks):
    """The scheme line with its marked words in color."""
    for word in marks:
        line = line.replace(word, f"{ACCENT}{BOLD}{word}{RESET}")
    return line


def text_lines(text, width):
    """Wrapped text: "- " starts a bullet, "$ " a command, "" leaves a blank line (air)."""
    out = []
    for line in text:
        if not line:
            out.append("")
        elif line.startswith("$ "):
            out.append(f"{CMD}{line}{RESET}")
        elif line.startswith("- "):
            parts = render.wrap(line[2:], width - 2, 4)
            out += ["• " + parts[0]] + ["  " + p for p in parts[1:]]
        else:
            out += render.wrap(line, width, 6)
    return out


def page_screen(lesson, n, cols, lines, breath=False, blink=False):
    """(row, col, text) pieces for page n of a lesson on a cols × lines terminal."""
    page = lesson["pages"][n]
    out = [(1, 2, f"{TITLE}{BOLD}🦉 {lesson['title']}{RESET} {DIM}· {n + 1}/{len(lesson['pages'])}{RESET}")]
    scheme = page.get("scheme", [])
    top = owl_top(lesson) if scheme else TOP
    marks = page.get("mark", [])
    for i, line in enumerate(scheme):
        out.append((top + i, LEFT, paint(line, marks)))
    point = page.get("point")
    col = owl_col(lesson)
    bottom = top + len(scheme)
    if col + OWL.width - 1 <= cols:
        row = top + point - WING if point is not None and scheme else top
        poses = (["inhale"] if breath else []) + (["closed"] if blink else [])
        cells = [[True] * OWL.width for _ in range(len(OWL.base) // 2)]
        for i, line in enumerate(render.lines(OWL, poses, cells)):
            out.append((row + i, col, line))
        if point is not None and scheme:
            end = LEFT + render.width(scheme[point].rstrip()) + 1
            out.append((top + point, end, LEADER + "┈" * (col - end) + RESET))
        bottom = max(bottom, row + len(OWL.base) // 2)
    elif point is not None and scheme:                     # no room for the owl: an arrow does its job
        end = LEFT + render.width(scheme[point].rstrip()) + 1
        out.append((top + point, end, f"{ACCENT}◂{RESET}"))
    row = bottom + 1 if scheme else TOP
    for line in text_lines(page.get("text", []), min(cols - LEFT - 1, 72)):
        if row < lines - 1:
            out.append((row, LEFT, line))
        row += 1
    last = n == len(lesson["pages"]) - 1
    keys = _("←/→: pages · Enter: finish the lesson · q: library") if last else _("←/→: pages · q: library")
    out.append((lines, 2, DIM + keys + RESET))
    return out


def group(lesson):
    skill = lesson.get("skill")
    return _(skills.SKILLS[skill]).split(":")[0] if skill else _("First steps")


class Library:
    def __init__(self, lessons, open_id=None):
        self.all = lessons
        self.s = state.load()
        self.lessons = shown(self.s, lessons)
        self.titles = {le["id"]: le["title"] for le in lessons}
        self.pos = 0
        self.lesson = None             # the lesson being read, or None on the list
        self.page = 0
        self.message = ""
        self.breath = self.blink = False
        news = [i for i, le in enumerate(self.lessons) if self.is_new(le)]
        self.pos = news[0] if news else next((i for i, le in enumerate(self.lessons)
                                              if unlocked(self.s, le) and le["id"] not in read(self.s)), 0)
        if open_id:
            found = next((i for i, le in enumerate(self.lessons) if le["id"] == open_id), None)
            if found is None:
                self.message = _("No lesson called {name}.").format(name=open_id)
            else:
                self.pos = found
                self.open()

    def is_new(self, le):
        return unlocked(self.s, le) and le["id"] not in progress_of(self.s)["opened"]

    def list_screen(self, cols, lines):
        done = sum(le["id"] in read(self.s) for le in self.lessons)
        out = [(1, 2, f"{TITLE}{BOLD}🦉 " + _("The Sage Owl's library") + f"{RESET} {DIM}· "
                + _("{n}/{total} read · ↑↓ Enter: open · q: quit").format(n=done, total=len(self.lessons)) + RESET)]
        rows, last = [], None
        for i, le in enumerate(self.lessons):
            if group(le) != last:
                last = group(le)
                rows.append((None, f"{BOLD}{last}{RESET}"))
            if le["id"] in read(self.s):
                mark, style = "✔", ""
            elif unlocked(self.s, le):
                mark, style = "📖", ""
            else:
                mark, style = "🔒", DIM
            new = f"  {ACCENT}" + _("new") + RESET if self.is_new(le) else ""
            text = f"{mark} {le['title']}"
            rows.append((i, (REV if i == self.pos else style) + f" {text} " + RESET + new))
        room = max(3, lines - 8)
        at = next(k for k, (i, _t) in enumerate(rows) if i == self.pos)
        start = max(0, min(at - room // 2, len(rows) - room))
        for k, (i, text) in enumerate(rows[start:start + room]):
            out.append((3 + k, 4 if i is not None else 2, text))
        le = self.lessons[self.pos]
        info = le["summary"] if unlocked(self.s, le) else _("To unlock: {how}").format(
            how=how_to_unlock(self.s, le, self.titles))
        below = 3 + min(room, len(rows)) + 1
        for k, part in enumerate(render.wrap(info, min(cols - 4, 76), 3)):
            out.append((below + k, 2, (ACCENT if not unlocked(self.s, le) else "") + part + RESET))
        if self.message:
            for k, part in enumerate(render.wrap(self.message, min(cols - 4, 76), 2)):
                out.append((lines - 2 + k, 2, DIM + part + RESET))
        return out

    def open(self):
        le = self.lessons[self.pos]
        if not unlocked(self.s, le):
            self.message = _("Not yet. To unlock it: {how}").format(how=how_to_unlock(self.s, le, self.titles))
            return
        with state.locked() as s:
            p = progress_of(s)
            if le["id"] not in p["opened"]:
                p["opened"].append(le["id"])
            self.page = min(p["page"].get(le["id"], 0), len(le["pages"]) - 1)
        self.s = state.load()
        self.lesson, self.message = le, ""

    def leave(self, finished=False):
        le = self.lesson
        before = {x["id"] for x in self.lessons if unlocked(self.s, x)}
        with state.locked() as s:
            p = progress_of(s)
            if finished:
                p["page"].pop(le["id"], None)
                if le["id"] not in p["read"]:
                    p["read"].append(le["id"])
            else:
                p["page"][le["id"]] = self.page
        self.s = state.load()
        self.lessons = shown(self.s, self.all)
        self.lesson = None
        if finished:
            opened = [x["title"] for x in self.lessons if unlocked(self.s, x) and x["id"] not in before]
            self.message = _("Lesson done: “{title}”.").format(title=le["title"]) + (
                " " + _("New: {titles}").format(titles=", ".join(opened)) if opened else "")
            self.pos = next((i for i, x in enumerate(self.lessons) if x["title"] in opened), self.pos)

    def key(self, k):
        if self.lesson:
            last = len(self.lesson["pages"]) - 1
            if k in ("right", "down"):
                self.page = min(last, self.page + 1)
            elif k in ("left", "up"):
                self.page = max(0, self.page - 1)
            elif k == "enter":
                if self.page == last:
                    self.leave(finished=True)
                else:
                    self.page += 1
            elif k == "quit":
                self.leave()
            return True
        if k in ("up", "left"):
            self.pos = (self.pos - 1) % len(self.lessons)
        elif k == "down":
            self.pos = (self.pos + 1) % len(self.lessons)
        elif k in ("enter", "right"):
            self.open()
            return True
        elif k == "quit":
            return False
        self.message = ""
        return True

    def draw(self):
        size = os.get_terminal_size()
        pieces = (page_screen(self.lesson, self.page, size.columns, size.lines, self.breath, self.blink)
                  if self.lesson else self.list_screen(size.columns, size.lines))
        out = [f"{ESC}[H{ESC}[2J"]
        for row, col, text in pieces:
            if 1 <= row <= size.lines:                     # below the last line the terminal would scroll
                out.append(f"{ESC}[{row};{col}H{text}")
        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def run(self):
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        sys.stdout.write(f"{ESC}[?1049h{ESC}[?25l{ESC}[?7l")         # no autowrap: a long line never spills
        try:
            tty.setcbreak(fd)
            running = True
            while running:
                self.draw()
                self.blink = False
                if not select.select([fd], [], [], 1.5)[0]:
                    self.breath = not self.breath
                    self.blink = random.random() < 0.15
                    continue
                data = os.read(fd, 8).decode(errors="ignore")
                running = self.key(KEYS.get(data, ""))
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
            sys.stdout.write(f"{ESC}[?7h{ESC}[?25h{ESC}[?1049l")
            sys.stdout.flush()
        done = sum(le["id"] in read(self.s) for le in self.lessons)
        print("  🦉 " + _("{n}/{total} lessons read. `bashou lesson` opens the library again.").format(
            n=done, total=len(self.lessons)))
        return 0


def run(lessons, open_id=None):
    return Library(lessons, open_id).run()
