"""The library screen of `bashou lesson`: the list of lessons, then a lesson page by page.

A page is a scheme (a small drawing in text) with the owl beside it, its wing pointing at the line that
matters, and a few short lines of text below. Words listed in "mark" stand out in the scheme: that's
usually what changed since the previous page.
"""

import os
import random
import sys

from .. import achievements, challenges, creatures, progress, render, skills, state, terminal
from ..adventure import quiz
from ..i18n import _
from . import (HERE, answered, by_id, depths, first_open, load, mastered, met, own, passed, progress_of, read,
               record_right, right, shown, skills_of, status, to_pass, unlocked, waiting_for)
from ..render import ESC, BOLD, DIM, RESET, REV, GOOD, BAD

ACCENT = f"{ESC}[38;2;240;200;110m"
CMD = f"{ESC}[38;2;130;210;120m"
TITLE = f"{ESC}[38;2;150;190;230m"
NEXT = f"{ESC}[38;2;120;220;150m"            # the lessons that make you progress now
LEADER = f"{ESC}[38;2;122;86;52m"            # the owl's outline brown: the dotted line is its gesture
KEYS = {" ": "right", "f": "f", "F": "f"}     # besides terminal.NAMES; f: path or whole library
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


NO_BREAK = {" :": "\u00a0:", " ;": "\u00a0;", " ?": "\u00a0?", " !": "\u00a0!", "« ": "«\u00a0", " »": "\u00a0»"}


def text_lines(text, width):
    """Wrapped text: "- " starts a bullet, "$ " a command, "" leaves a blank line (air).
    French spaces before : ; ? ! and inside « » never start or end a line."""
    def keep(text):
        for space, kept in NO_BREAK.items():
            text = text.replace(space, kept)
        return text

    out = []
    for line in text:
        if not line:
            out.append("")
        elif line.startswith("$ "):
            out.append(f"{CMD}{line}{RESET}")
        elif line.startswith("- "):                      # the bullet first: "- ? is…" stays a bullet
            parts = render.wrap(keep(line[2:]), width - 2, 4)
            out += ["• " + parts[0]] + ["  " + p for p in parts[1:]]
        else:
            out += render.wrap(keep(line), width, 6)
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
    col = owl_col(lesson) if scheme else cols - OWL.width     # no drawing: the owl stands at the right
    width = min(cols - LEFT - 1, 72) if scheme else min(col - LEFT - 2, 72)
    bottom = top + len(scheme)
    if col + OWL.width - 1 <= cols and (scheme or width >= 40):
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
    if not scheme and width < 40:                           # too narrow for both: the text gets the room
        width = min(cols - LEFT - 1, 72)
    for line in text_lines(page.get("text", []), width):
        if row < lines - 1:
            out.append((row, LEFT, line))
        row += 1
    last = n == len(lesson["pages"]) - 1
    keys = _("←/→: pages · Enter: finish the lesson · q: library") if last else _("←/→: pages · q: library")
    out.append((lines, 2, DIM + keys + RESET))
    return out


def section(lesson):
    """The library section of a lesson: its first skill, "git" for git (no skill, open to all), else "first"."""
    return next(iter(skills_of(lesson)), "git" if lesson["id"] == "git" else "first")


SECTIONS = ["first", "git", *skills.SKILLS]           # the order of the whole library


def group(lesson):
    key = section(lesson)
    return {"first": _("First steps"), "git": _("Git")}.get(key) or _(skills.SKILLS[key].text).split(":")[0]


def by_section(lessons):
    """Each section once, in SECTIONS order, its lessons in their own order (the path still crosses them)."""
    return sorted(lessons, key=lambda le: (SECTIONS.index(section(le)), le["order"]))


PATH = 10            # lessons on your path, the library's first view (owner: or we lose people in lessons)
AHEAD = 2            # of them, locked ones at least, when there are: what opens next


def path(s, lessons):
    """Your next lessons: the open ones not mastered, unread first, nearest the start first, then a few
    locked ones to show what's ahead."""
    depth = depths()
    rank = lambda le: (le["id"] in read(s), depth.get(le["id"], 1), le["order"])
    open_ = sorted((le for le in lessons if status(s, le) == "next"), key=rank)
    locked = sorted((le for le in lessons if status(s, le) == "locked"),     # the nearest to open first
                    key=lambda le: (sum(not unlocked(s, b) for b in waiting_for(s, le)), *rank(le)))
    keep = max(PATH - AHEAD, PATH - len(locked))
    found = open_[:keep]
    return found + locked[:PATH - len(found)]


def for_shell(lessons, shell):
    """The lessons with only the pages for your shell: a page that says "shell": "zsh" tells what zsh does
    differently, for zsh players only (0.9.0)."""
    return [dict(le, pages=[p for p in le["pages"] if p.get("shell", shell) == shell]) for le in lessons]


def for_editor(lessons, editor):
    """The lessons with only the pages of your editor (`bashou config editor`): a page may say
    "editor": "nano" or "vi"."""
    return [dict(le, pages=[p for p in le["pages"] if p.get("editor", editor) == editor]) for le in lessons]


def for_os(lessons, systems):
    """The lessons and pages about the systems you learn (`bashou config os`): a lesson or a page may say
    "os": "linux" or "macos" (macOS, 2026-10-13)."""
    return [dict(le, pages=[p for p in le["pages"] if skills.shows(p, systems)])
            for le in lessons if skills.shows(le, systems)]


# --- warm-up: a few questions on the lessons before, the first time a lesson opens (owner) ------------

WARMUP = 2


def recall_ids(s, lesson):
    """The `recall` questions of the lessons this one comes after (those of skills you learn)."""
    lessons = by_id()
    ids = []
    for before in (lessons[p] for p in lesson.get("after", [])):
        if not skills_of(before) or any(skills.wanted(s, k) for k in skills_of(before)):
            ids += [q for q in before.get("recall", []) if q not in ids]
    return ids


END_QUIZ = 4         # questions at the end of a lesson that passes with right answers ("answered")


def questions(s, ids, n, rng):
    """Up to n of these questions (those of your systems), their choices shuffled like in the adventure."""
    systems = skills.oses(s)
    pool = []
    for qid in ids:
        q = next((q for q in quiz.bank(qid.rsplit("-", 2)[0]) if q["id"] == qid), None)
        if q and skills.shows(q, systems):                  # not a Linux question on a Mac
            pool.append(q)
    found = []
    for q in rng.sample(pool, min(n, len(pool))):
        order = list(range(len(q["choices"])))
        rng.shuffle(order)
        found.append({**q, "choices": [q["choices"][i] for i in order], "answer": order.index(q["answer"])})
    return found


def warmup(s, lesson, rng=None):
    """Up to WARMUP questions on the lessons before this one."""
    return questions(s, recall_ids(s, lesson), WARMUP, rng or random.Random())


def end_quiz(s, lesson, rng=None):
    """Up to END_QUIZ of the lesson's own questions you haven't answered right yet."""
    done = set(right(s))
    return questions(s, [q for q in lesson.get("questions", []) if q not in done], END_QUIZ, rng or random.Random())


def warmup_screen(lesson, questions, total, pos, chosen, cols, lines, final=False):
    """(row, col, text) pieces: the question, its choices, and once answered, the explanation. `final`:
    the quiz at the end of the lesson instead of the warm-up."""
    q = questions[0]
    width = min(cols - 4, 76)
    head = "🦉 " + (_("Quiz: “{title}”") if final else _("Warm-up before “{title}”")).format(title=lesson["title"]) \
        + f" · {total - len(questions) + 1}/{total}"
    out = [(1 + k, 2, part) for k, part in enumerate(render.fit(f"{TITLE}{BOLD}{head}", width))]
    row = len(out) + 2
    why = _("Show what you understood: {n} right answers to this lesson's questions pass it, here or "
            "in the adventure.").format(n=next((c.split()[2] for c in lesson.get("masters", [])
                                               if c.startswith("answered ")), END_QUIZ)) if final \
        else _("What you learned just before: does it still come back?")
    for part in render.wrap(why, width, 2):
        out.append((row, 2, DIM + part + RESET))
        row += 1
    row += 1
    for part in render.wrap(q["q"], width, 5):
        out.append((row, 2, BOLD + part + RESET))
        row += 1
    row += 1
    for i, choice in enumerate(q["choices"]):
        if chosen is None:
            style, mark = (REV if i == pos else ""), " "
        else:
            style, mark = ((GOOD, "✔") if i == q["answer"] else (BAD, "✘") if i == chosen else (DIM, " "))
        for k, part in enumerate(render.wrap(choice, width - 4, 3)):
            out.append((row, 3, f"{style}{mark if k == 0 else ' '} {part} {RESET}"))
            row += 1
    if chosen is not None:
        row += 1
        verdict = _("Right!") if chosen == q["answer"] else _("Not quite.")
        for part in render.wrap(verdict + " " + q["explain"], width, 12):
            out.append((row, 2, part))
            row += 1
        keys = _("Enter: next question") if len(questions) > 1 else \
            _("Enter: close the lesson") if final else _("Enter: open the lesson")
    else:
        keys = _("↑/↓, Enter: answer · q: skip the quiz") if final else _("↑/↓, Enter: answer · q: skip the warm-up")
    out.append((lines, 2, DIM + keys + RESET))
    return out


class Library:
    def __init__(self, lessons, open_id=None):
        self.s = state.load()
        shell = "zsh" if os.environ.get("BASHOU_SHELL") == "zsh" else "bash"     # the loaders export it
        self.all = lessons = for_os(for_shell(for_editor(lessons, state.setting(self.s, "editor")), shell),
                                    skills.oses(self.s))
        self.quiz, self.choice, self.chosen = [], 0, None     # the warm-up or the end quiz, while it's on
        self.final = False                                    # the quiz is the end quiz
        self.full = False              # the whole library, or only your path (the first view)
        self.lessons = self.view()
        self.pos = 0
        self.lesson = None             # the lesson being read, or None on the list
        self.page = 0
        self.message = ""
        self.breath = self.blink = False
        self.pos = self.next_step()
        if open_id:
            if not self.go(open_id):
                self.message = _("No lesson called {name}.").format(name=open_id)
            else:
                self.open()

    def all_shown(self):
        return shown(self.s, self.all)

    def view(self):
        """The rows of the list: your path, or every lesson, section by section. Never empty: once all
        is mastered, the path shows the whole library."""
        lessons = self.all_shown()
        return by_section(lessons) if self.full else path(self.s, lessons) or by_section(lessons)

    def go(self, lesson_id):
        """Put the cursor on a lesson, in the whole library if it isn't on your path. False if there's none."""
        if all(le["id"] != lesson_id for le in self.lessons) and not self.full:
            self.full = True
            self.lessons = self.view()
        found = next((i for i, le in enumerate(self.lessons) if le["id"] == lesson_id), None)
        if found is not None:
            self.pos = found
        return found is not None

    def toggle(self):
        at = self.lessons[self.pos]["id"]
        self.full = not self.full
        self.lessons = self.view()
        self.pos = next((i for i, le in enumerate(self.lessons) if le["id"] == at), None)
        if self.pos is None:
            self.pos = self.next_step()

    def next_step(self, default=0):
        """Where the cursor goes: a lesson that makes you progress, new or unread ones first."""
        ranked = [(not self.is_new(le), le["id"] in read(self.s), i) for i, le in enumerate(self.lessons)
                  if status(self.s, le) == "next"]
        return min(ranked)[2] if ranked else default

    def is_new(self, le):
        return unlocked(self.s, le) and le["id"] not in progress_of(self.s)["opened"]

    def list_screen(self, cols, lines):
        every = self.all_shown()
        done = sum(le["id"] in read(self.s) for le in every)
        keys = _("{n}/{total} read · ↑↓ Enter: open · f: your path · q: quit") if self.full \
            else _("{n}/{total} read · ↑↓ Enter: open · f: whole library · q: quit")
        head = render.heading("🦉 " + (_("The Sage Owl's library") if self.full else _("Your path in the library")),
                              keys.format(n=done, total=len(every)), cols - 1)
        out = [(1 + k, 2, TITLE + line) for k, line in enumerate(head)]
        top = len(head) - 1                                 # the keys took a line of their own (portrait)
        out.append((2 + top, 2, NEXT + "■ " + _("your next step") + f"{RESET}  ■ " + _("mastered") + f"  {DIM}🔒 "
                    + _("waits for another lesson") + RESET))
        rows, last = [], None
        align = 2 + max((render.width(f" 🔒 {le['title']} ") for le in self.lessons), default=0)
        avail = cols - 4 - 1
        for i, le in enumerate(self.lessons):
            if self.full and group(le) != last:
                last = group(le)
                rows.append((None, f"{BOLD}{last}{RESET}"))
            st = status(self.s, le)
            mark = "🔒" if st == "locked" else "✔" if le["id"] in read(self.s) else "📖"
            style = {"locked": DIM, "next": NEXT, "mastered": ""}[st]
            new = f"  {ACCENT}" + _("new") + RESET if self.is_new(le) else ""
            text = f" {mark} {le['title']} "
            if st == "locked":
                new = tail(text, after(self.s, le) if self.full else f"{group(le)} · {after(self.s, le)}", align, avail)
            elif not self.full:                       # the path mixes sections: each row names its own
                new = tail(text, group(le), align, avail) + new
            rows.append((i, (REV if i == self.pos else "") + style + text + RESET + new))
        le = self.lessons[self.pos]
        st = status(self.s, le)
        width = min(cols - 4, 76)
        if st == "locked":
            info = unlock_lines(self.s, le, width)
        elif st == "next":
            info = [(part, "") for part in render.wrap(le["summary"], width, 3)] + [
                (part, NEXT) for part in render.wrap(_("Your next step. To master it: {how}").format(
                    how=missing(self.s, le["masters"])), width, 3)]
        else:
            info = [(part, "") for part in render.wrap(le["summary"], width, 3)] + [
                (part, DIM) for part in render.wrap(
                    _("Mastered: you already do what it teaches. Read it again any time."), width, 3)]
        note = render.wrap(self.message, width, 5) if self.message else []
        room = max(3, lines - 8 - top - (len(info) if st == "locked" else 3)    # a locked lesson's why takes room
                   - max(0, len(note) - 3))
        at = next(k for k, (i, _t) in enumerate(rows) if i == self.pos)
        start = max(0, min(at - room // 2, len(rows) - room))
        for k, (i, text) in enumerate(rows[start:start + room]):
            out.append((4 + top + k, 4 if i is not None else 2, text))
        row = 4 + top + min(room, len(rows)) + 1
        for part, color in info:
            if row < lines - max(3, len(note)):
                out.append((row, 2, color + part + RESET))
            row += 1
        for k, part in enumerate(note):
            out.append((lines - max(3, len(note)) + k, 2, DIM + part + RESET))
        return out

    def open(self):
        le = self.lessons[self.pos]
        if not unlocked(self.s, le):
            start = first_open(self.s, le)
            if not (start and self.go(start["id"])):
                self.message = _("Not yet. To unlock it: {how}").format(how=how_to_unlock(self.s, le))
                return
            at = self.pos
            self.message = _("“{title}” isn't open yet: lessons follow each other. The cursor moved to "
                             "“{start}”, the open lesson to practice first.").format(
                title=short(le["title"]), start=short(self.lessons[at]["title"]))
            return
        if le["id"] not in progress_of(self.s)["opened"]:
            self.quiz, self.choice, self.chosen = warmup(self.s, le), 0, None
            self.quiz_total = len(self.quiz)
        with state.locked() as s:
            p = progress_of(s)
            if le["id"] not in p["opened"]:
                p["opened"].append(le["id"])
            self.page = min(p["page"].get(le["id"], 0), len(le["pages"]) - 1)
        self.s = state.load()
        self.lesson, self.message = le, ""

    def leave(self, finished=False):
        le = self.lesson
        notes = []
        with state.locked() as s:
            p = progress_of(s)
            if finished:
                p["page"].pop(le["id"], None)
                if le["id"] not in p["read"]:
                    p["read"].append(le["id"])
                notes = progress.check(s)                  # the Spark's achievements come from reading
            else:
                p["page"][le["id"]] = self.page
        self.s = state.load()
        self.lessons = self.view()
        self.pos = next((i for i, other in enumerate(self.lessons) if other["id"] == le["id"]), None)
        if self.pos is None:                           # off the path now: on to the next step
            self.pos = self.next_step()
        self.lesson = None
        if finished:
            self.message = _("Lesson done: “{title}”.").format(title=le["title"])
            waiting = [w for w in self.all_shown() if le["id"] in w.get("after", []) and not unlocked(self.s, w)]
            hard = [w for w in waiting if w.get("opens") == "mastered"]
            waiting = [w for w in waiting if w not in hard]
            if waiting and not passed(self.s, le):     # bug report: players thought reading opens the next one
                ways = ways_to_pass(self.s, le)
                self.message += " " + _("Reading isn't enough to open {lessons}: practice this one first. "
                                        "Any one is enough: {ways}.").format(
                    lessons=_(" and ").join(_("“{name}”").format(name=short(w["title"])) for w in waiting),
                    ways=", ".join(ways[:-1]) + _(", or ") + ways[-1] if len(ways) > 1 else ways[0])
            elif hard and not mastered(self.s, le):
                self.message += " " + _("{lessons} opens once you have mastered this one: {how}.").format(
                    lessons=_(" and ").join(_("“{name}”").format(name=short(w["title"])) for w in hard),
                    how=missing(self.s, le["masters"]))
            elif status(self.s, le) == "next":
                self.message += " " + _("Now practice it: fights and achievements make it mastered.")
            if notes:
                self.message += " " + " ".join(notes)

    def finish(self):
        """The last page read: the end quiz if the lesson has one, then back to the list."""
        self.quiz, self.choice, self.chosen = end_quiz(self.s, self.lesson), 0, None
        self.quiz_total, self.final = len(self.quiz), bool(self.quiz)
        if not self.quiz:
            self.leave(finished=True)

    def warmup_key(self, k):
        if k == "quit":
            self.quiz = []
        elif self.chosen is None:
            if k in ("up", "left"):
                self.choice = (self.choice - 1) % len(self.quiz[0]["choices"])
            elif k in ("down", "right"):
                self.choice = (self.choice + 1) % len(self.quiz[0]["choices"])
            elif k == "enter":
                self.chosen = self.choice
                if self.chosen == self.quiz[0]["answer"]:
                    with state.locked() as s:
                        record_right(s, self.quiz[0]["id"])
                    self.s = state.load()
        elif k == "enter":
            self.quiz, self.choice, self.chosen = self.quiz[1:], 0, None
        if not self.quiz and self.final:
            self.final = False
            self.leave(finished=True)
        return True

    def key(self, k):
        if self.lesson and self.quiz:
            return self.warmup_key(k)
        if self.lesson:
            last = len(self.lesson["pages"]) - 1
            if k in ("right", "down"):
                self.page = min(last, self.page + 1)
            elif k in ("left", "up"):
                self.page = max(0, self.page - 1)
            elif k == "enter":
                if self.page == last:
                    self.finish()
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
        elif k == "f":
            self.toggle()
        elif k == "quit":
            return False
        self.message = ""
        return True

    def screen(self, cols, lines):
        if self.lesson and self.quiz:
            return warmup_screen(self.lesson, self.quiz, self.quiz_total, self.choice, self.chosen, cols, lines, self.final)
        if self.lesson:
            return page_screen(self.lesson, self.page, cols, lines, self.breath, self.blink)
        return self.list_screen(cols, lines)

    def draw(self):
        size = os.get_terminal_size()
        pieces = self.screen(size.columns, size.lines)
        out = [f"{ESC}[H{ESC}[2J"]
        for row, col, text in pieces:
            if 1 <= row <= size.lines:                     # below the last line the terminal would scroll
                out.append(f"{ESC}[{row};{col}H{text}")
        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def run(self):
        with terminal.Screen() as screen:
            running = True
            while running:
                self.draw()
                self.blink = False
                keys = screen.keys(1.5)
                if not keys:
                    self.breath = not self.breath
                    self.blink = random.random() < 0.15
                for k in keys:
                    running = running and self.key(terminal.name(k, KEYS))
        every = self.all_shown()
        done = sum(le["id"] in read(self.s) for le in every)
        print("  🦉 " + _("{n}/{total} lessons read. `bashou lesson` opens the library again.").format(
            n=done, total=len(every)))
        return 0


def run(lessons, open_id=None):
    return Library(lessons, open_id).run()


# --- what's still missing, in words ---------------------------------------------------------

def describe(cond, s=None):
    """A condition in words for the list: "beat the Semicolon slug", "run 50 commands (32/50)"."""
    kind, *args = cond.split()
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
    if kind == "answered":
        text = _("answer {n} of its questions right").format(n=args[1])
        return text + (f" ({min(answered(s, args[0]), int(args[1]))}/{args[1]})" if s else "")
    return cond


def missing(s, conds):
    """What still doesn't hold, in words: "run 50 commands (32/50) · beat the Leak Lurker in a fight"."""
    left = []
    for cond in conds:
        sides = [c.strip() for c in cond.split("|")]
        if not any(met(s, c) for c in sides):
            left.append(_(" or ").join(describe(c, s) for c in sides))
    return " · ".join(left)


def short(title):
    """A lesson's title without what follows its colon: "Files" for "Files: make, copy, move, delete"."""
    return title.split(":")[0].strip()


def titles():
    return {le["id"]: le["title"] for le in load()}


def after(s, lesson):
    """What a locked row says on its right: "after Files" (the lessons it still waits for)."""
    names = titles()
    return _("after {lessons}").format(
        lessons=", ".join(short(names.get(b["id"], b["title"])) for b in waiting_for(s, lesson)))


def tail(text, note, align, avail):
    """The dim note on the right of a list row: lined up with the others when there is room, right
    after the title when there isn't, cut with … when even that is too long."""
    used = render.width(text)
    pad = align - used if align + render.width(note) <= avail else 1
    if used + pad + render.width(note) > avail:
        room = avail - used - pad
        if room < 8:
            return ""
        note = render.wrap(note, room, 1)[0]
    return f"{DIM}{LEADER}{'·' * (pad - 1)}{RESET}{DIM} {note}{RESET}"


def ways_to_pass(s, before):
    """The ways to get through a lesson, any one is enough: "win one of its fights", "earn “Builder”",
    "use mkdir once (0/1)", "earn 6 achievements in all (2/6)"."""
    ways = [_("win one of its fights")] if before.get("fights") else []
    names = [_("“{name}”").format(name=_(a.name)) for cond in before.get("masters", [])
             for c in cond.split("|") if c.split()[0] == "achievement"
             for a in achievements.ALL if a.id == c.split()[1]]
    if names:
        ways.append(_("earn {achievements}").format(achievements=_(" or ").join(names)))
    tools = own(before, "tool") + own(before, "answered")
    if tools:
        ways.append(_(" or ").join(describe(" ".join(t), s) for t in tools))
    n = to_pass(before)
    ways.append(_("earn {n} achievements in all").format(n=n) + f" ({len(s['achievements'])}/{n})")
    return ways


def shortcut(lesson):
    """The first fight of a lesson: meeting it opens the lesson at once."""
    return next((challenges.BY_ID[f] for f in lesson.get("fights", []) if f in challenges.BY_ID), None)


def how_to_unlock(s, lesson):
    """The lessons still to practice before this one, and the ways to get through each, on one line:
    "practice “Paths”: win one of its fights, earn “Builder”, or earn 6 achievements in all (2/6)".
    An easy lesson asks to read the one before, a hard one to master it."""
    names = titles()
    parts = []
    for before in waiting_for(s, lesson):
        name = names.get(before["id"], before["title"])
        if lesson.get("opens") == "read":
            parts.append(_("read “{lesson}”").format(lesson=name))
            continue
        if lesson.get("opens") == "mastered":
            parts.append(_("master “{lesson}”: {how}").format(lesson=name, how=missing(s, before["masters"])))
            continue
        ways = ways_to_pass(s, before)
        parts.append(_("practice “{lesson}”: {ways}").format(lesson=name,
                                                            ways=", ".join(ways[:-1]) + _(", or ") + ways[-1]
                                                            if len(ways) > 1 else ways[0]))
    text = " · ".join(parts)
    first = shortcut(lesson)
    if first:
        text += " " + _("(or meet the {threat} in a fight)").format(threat=_(first.threat))
    return text


def unlock_lines(s, lesson, width):
    """Why a lesson is locked and how to open it, for the bottom of the list: (line, color) pairs.
    Players saw padlocks without knowing why: say that lessons follow each other, what to practice,
    and where to start when the lesson before is locked too."""
    names = titles()
    quoted = lambda le: _("“{name}”").format(name=short(names.get(le["id"], le["title"])))
    befores = waiting_for(s, lesson)
    opens = lesson.get("opens")
    why = {"read": _("🔒 {title} builds on {lessons}. Lessons follow each other: this one opens once you have "
                     "read what comes before."),
           "mastered": _("🔒 {title} builds on {lessons}. It's a hard one: it opens once you have mastered "
                         "what comes before.")}.get(opens, _(
               "🔒 {title} builds on {lessons}. Lessons follow each other: this one opens once you have "
               "practiced what comes before."))
    lines = [(part, ACCENT) for part in render.wrap(why.format(
        title=short(lesson["title"]), lessons=_(" and ").join(quoted(b) for b in befores)), width, 4)]
    ways = []
    for before in befores:
        if opens == "read":
            ways += [(part, "") for part in render.wrap(
                _("Read {lesson} to the end.").format(lesson=quoted(before)), width, 2)]
            continue
        if opens == "mastered":
            ways += [(part, "") for part in render.wrap(
                _("To master {lesson}: {how}.").format(lesson=quoted(before), how=missing(s, before["masters"])),
                width, 2)]
            continue
        ways += [(part, "") for part in render.wrap(
            _("To practice {lesson}, any one of these is enough:").format(lesson=quoted(before)), width, 2)]
        ways += [(part, "") for part in text_lines(["- " + way for way in ways_to_pass(s, before)], width)]
    locked = [b for b in befores if not unlocked(s, b)]
    start = first_open(s, lesson)
    if locked and start:
        text = (_("{lesson} is locked too.") if len(locked) == 1 else _("{lesson} are locked too.")).format(
            lesson=_(" and ").join(quoted(b) for b in locked))
        text += " " + _("Start with {start}: it's open. Enter takes you there.").format(start=quoted(start))
        lines += [(part, NEXT) for part in render.wrap(text, width, 3)]
    elif start:
        lines += [(part, NEXT) for part in render.wrap(
            _("Enter takes you to {start}.").format(start=quoted(start)), width, 2)]
    lines += ways                                     # after where to start: a short screen cuts these first
    first = shortcut(lesson)
    if first:
        lines += [(part, DIM) for part in render.wrap(
            _("Shortcut: meeting the {threat} in a fight opens this lesson at once.").format(
                threat=_(first.threat)), width, 2)]
    return lines


# --- `bashou lesson` ------------------------------------------------------------------------

def main(args):
    lessons = load()
    s = state.load()
    if args and args[0] == "list" or not sys.stdin.isatty():
        return print_list(s, lessons)
    return run(lessons, args[0] if args else None)


def print_list(s, lessons):
    """`bashou lesson list` (or outside a terminal): the library as text."""
    for le in shown(s, lessons):
        mark = "✔" if le["id"] in read(s) else "📖"
        st = status(s, le)
        if st == "next":
            print(f"  {mark} {NEXT}{le['title']}{RESET}  \x1b[2m{le['summary']}\x1b[0m")
        elif st == "mastered":
            print(f"  {mark} {le['title']}")
        else:
            print(f"  \x1b[2m🔒 {le['title']} · {after(s, le)} · {how_to_unlock(s, le)}\x1b[0m")
    return 0
