"""Every main screen, drawn by the real code at three terminal sizes: a full screen, a portrait one and a
small one (a quarter of the full one). Nothing may be drawn past the right edge or below the last row:
there the terminal wraps or scrolls, and the picture breaks.

    BASHOU_SHOTS=/tmp/shots python3 -m unittest tests.test_screens    # also saves each screen as an SVG
"""

import contextlib
import importlib.util
import io
import json
import os
import random
import re
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from bashou import challenges, cli, companion, creatures, duel, evolve, fight, progress, starter, state
from bashou.adventure import game
from bashou.lesson import load as load_lessons, reader

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("screenshot", ROOT / "tools/screenshot.py")
screenshot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(screenshot)

SIZES = {"full": (160, 48), "portrait": (60, 96), "small": (80, 24)}
TINY = (40, 12)                                                  # a very small window
RUNS = {"level": [], "pets": ["pets"], "achievements": ["achievements"], "evolve": ["evolve"], "swap": ["swap"],
        "stats": ["stats"], "share": ["share", "--name", "Tester"], "lesson": ["lesson"], "project": ["project"], "spot": ["spot"],
        "learn": ["learn", "grep", "-rn", "TODO", "."], "talk": ["talk"], "fight": ["fight"], "arena": ["arena"],
        "adventure": ["adventure"], "on": ["on"], "off": ["off"], "config": ["config", "list"], "start": ["start"],
        "reset": ["reset"], "version": ["version"], "help": ["help"]}
NOT_RUN = {"update"}                                             # git or apt/dnf: not in a test
DRAWN = "▀▄█░▌▐"                                                 # sprites, bars, QR codes


def last_drawn(line):
    """Up to the last drawn character: a sentence may wrap like in any terminal, a drawing may not."""
    return max((i + 1 for i, ch in enumerate(line) if ch in DRAWN), default=0)


SMALLEST = {c.name: c.size for c in cli.COMMANDS if c.size}      # below it, the command says so and stops


def sizes(command):
    """The three sizes, and the smallest one the command accepts."""
    return [*SIZES, f"smallest {command}"]
SEQ = re.compile(r"\x1b\[(\??)([0-9;]*)([A-Za-z])|\x1b([78])")


class Term(screenshot.Screen):
    """A terminal that notes what goes off screen instead of hiding it. `flow`: plain printed text,
    which may wrap and scroll like in any terminal (commands' output)."""

    def __init__(self, cols, rows, flow=False):
        super().__init__(cols, rows)
        self.flow, self.off = flow, []

    def put(self, ch):
        if ch == "\r":
            self.c = 0
            return
        if ch == "\n" or (self.flow and self.c >= self.cols):
            self.r, self.c = self.r + 1, 0
            if self.flow and self.r >= self.rows:                    # scroll up
                self.cells = self.cells[1:] + [[(" ", None, None, False) for _ in range(self.cols)]]
                self.r = self.rows - 1
            if ch == "\n":
                return
        if ch.strip() or ch == " ":
            if self.c + max(1, screenshot.render.width(ch)) > self.cols or self.r >= self.rows or self.r < 0:
                self.off.append((self.r + 1, self.c + 1, ch))
        super().put(ch)

    def write(self, text):
        pos = 0
        for m in SEQ.finditer(text):
            for ch in text[pos:m.start()]:
                self.put(ch)
            pos = m.end()
            private, params, cmd, esc = m.groups()
            n = int(params) if params.isdigit() else 1
            if private:
                continue                                              # modes: alternate screen, cursor…
            if esc == "7":
                self.saved = (self.r, self.c)
            elif esc == "8":
                self.r, self.c = self.saved
            elif cmd == "H":
                r, _, c = (params or "1;1").partition(";")
                self.r, self.c = int(r or 1) - 1, int(c or 1) - 1
            elif cmd in "ABCD":
                dr, dc = {"A": (-n, 0), "B": (n, 0), "C": (0, n), "D": (0, -n)}[cmd]
                self.r, self.c = max(0, self.r + dr), max(0, self.c + dc)
            elif cmd == "K" and 0 <= self.r < self.rows:
                self.cells[self.r][self.c:] = [(" ", None, None, False)] * (self.cols - min(self.c, self.cols))
            elif cmd == "J":
                self.cells = [[(" ", None, None, False) for _ in range(self.cols)] for _ in range(self.rows)]
            elif cmd == "m":
                self.sgr(params)
        for ch in text[pos:]:
            self.put(ch)

    def text(self):
        return "\n".join("".join(ch for ch, *_ in row) for row in self.cells)


def printed(function, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        function(*args)
    return out.getvalue()


class ScreensTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        data = Path(self.tmp.name)
        for patch in (mock.patch.object(state, "DATA", data), mock.patch.object(state, "STATE", data / "state.json"),
                      mock.patch.object(state, "CACHE", data / "cache"),
                      mock.patch("bashou.which.installed", return_value=True), mock.patch.dict(os.environ, {"BASHOU_LANG": "en"})):
            patch.start()
            self.addCleanup(patch.stop)
        with state.locked() as s:                  # a player some way in: pets, forms, a few lessons read
            s.update(starter="star", language="en", commands=620, fights_won=3,
                     achievements=[a.id for a in progress.achievements.ALL if not a.hidden][:24],
                     pets=["bat", "frog", "fox", "mole", "slime", "owl"], active="fox",
                     tools={"grep": 40, "find": 12, "awk": 9}, days=["2026-09-28", "2026-09-29"])
            s["lessons"]["read"] = [load_lessons("en")[0]["id"]]
        self.shots = os.environ.get("BASHOU_SHOTS")

    def check(self, name, size, term, *visible):
        """Nothing off screen, and what matters shows. Saves the picture with BASHOU_SHOTS."""
        if self.shots:
            Path(self.shots).mkdir(parents=True, exist_ok=True)
            (Path(self.shots) / f"{size}-{name}.svg").write_text(term.svg(f"{name} · {size} {term.cols}×{term.rows}"))
        self.assertEqual(term.off[:5], [], f"{name} at {size}: drawn off screen (row, column, character)")
        for text in visible:
            self.assertIn(text, term.text(), f"{name} at {size}")

    @contextlib.contextmanager
    def at(self, size):
        cols, rows = SIZES.get(size) or SMALLEST[size.split()[1]]
        with self.subTest(size=size), mock.patch("os.get_terminal_size", return_value=os.terminal_size((cols, rows))):
            yield cols, rows

    def test_board(self):
        from bashou import board
        for size in sizes("swap"):
            with self.at(size) as (cols, rows):
                b = board.Board()
                t = Term(cols, rows)
                t.write(printed(b.draw))
                self.check("board", size, t, "Fox" if size in SIZES else "Bashou")   # smallest: Fox is a row below

    def test_library_and_a_lesson(self):
        lessons = load_lessons("en")
        for size in sizes("lesson"):
            with self.at(size) as (cols, rows):
                lib = reader.Library(lessons)
                t = Term(cols, rows)
                t.write(printed(lib.draw))
                self.check("library", size, t, lessons[0]["title"])
                lib = reader.Library(lessons, lessons[0]["id"])
                t = Term(cols, rows)
                t.write(printed(lib.draw))
                self.check("lesson", size, t)
                with state.locked() as s:                  # the warm-up comes the first time only
                    s["lessons"]["opened"] = [le for le in s["lessons"]["opened"] if le != "help"]
                lib = reader.Library(lessons, "help")
                self.assertTrue(lib.quiz)
                for name in ("warm-up", "warm-up-answer"):
                    t = Term(cols, rows)
                    t.write(printed(lib.draw))
                    self.check(name, size, t, "Warm-up")
                    lib.key("enter")

    def test_first_launch_pickers(self):
        screens = {"starter": lambda: starter.draw(0, False), "language": lambda: starter.draw_languages(0, False),
                   "skills-mode": lambda: starter.draw_mode(1, False),
                   "skills": lambda: starter.checklist_drawer({"bash"})(0, False),
                   "editor": lambda: starter.draw_editor(0, False)}
        for size in sizes("start"):
            with self.at(size) as (cols, rows):
                for name, draw in screens.items():
                    t = Term(cols, rows)
                    t.write(printed(draw))
                    self.check(name, size, t)

    def test_adventure(self):
        for size in sizes("adventure"):
            with self.at(size) as (cols, rows):
                with state.locked() as s:           # a new walk at each size, not the last size's saved one
                    s["adventure"] = {}
                g = game.Game(cols, rows, rng=random.Random(0))
                t = Term(cols, rows)                  # one terminal: each frame only redraws what changed
                for phase, keys in (("intro", ()), ("fork", ("\r",)), ("walk", ("\r",))):
                    for k in keys:
                        g.key(k, 100.0)
                    t.write(g.draw(1.0, 100.0) + g.hud())
                    self.check(f"adventure-{phase}", size, t, "♥")
                for _ in range(200):                                      # walk up to the first monster
                    g.update(0.5, 100.0)
                    if g.adv["phase"] != "walk":
                        break
                t.write(g.draw(1.0, 100.0) + g.hud())
                self.check("adventure-monster", size, t, "A.", "♥")
                top, _left, _width, wrapped = g.panel_rect         # owner: the question box hid the pet
                pet_top = (g.canvas.h - 12 * g.scale - 1) // 2 + 1
                self.assertLess(top + len(wrapped) + 1, pet_top, f"{size}: the box covers the pet")

    def test_evolution(self):
        s = state.load()
        e = {"who": "fox", "from": "fennec", "to": "fox"}
        for size in sizes("evolve"):
            with self.at(size) as (cols, rows):
                screen = evolve.Screen()
                t = Term(cols, rows)
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    for title, lines, text, _seconds in evolve.scenes(s, e):
                        screen.show(title, lines, text)
                t.write(out.getvalue())
                self.check("evolve", size, t, "Fox")

    def test_the_pet_at_the_prompt(self):
        for size in SIZES:
            with self.at(size) as (cols, rows):
                pet = companion.Companion(os.getpid())
                pet.bubble = ("Try `grep -rn TODO .` (achv: Digger) and see what your notes hide.", 0, 5)
                t = Term(cols, rows)
                t.write("\x1b[10;1Hme@laptop:~$ ")
                body, _erase = pet.frame(0, [], "", cols)
                t.write(body)
                self.check("prompt", size, t, "Digger")

    def test_fight_panel(self):
        ch = challenges.BY_ID["grep_hydra"]
        for size in SIZES:
            with self.at(size) as (cols, rows):
                base = Path(self.tmp.name) / f"arena-{size}"
                (base / "arena").mkdir(parents=True)
                meta = {"challenge": ch.id, "hints": 0, **ch.setup(base / "arena", random.Random(3))}
                (base / "meta.json").write_text(json.dumps(meta))
                (base / "duel.json").write_text(json.dumps({"hearts": 2, "enemy": 2, "offset": 0, "event": "hit",
                                                            "at": 0, "said": "💥 grep hits the Log Hydra!"}))
                scene = duel.Scene(base, 0)
                t = Term(cols, rows)
                if scene.fits(cols):
                    t.write(scene.frame(cols, time.time())[0])
                t.write(f"\x1b[{scene.height() + 2};1H")
                t.flow = True
                t.write(fight.banner(ch, ch.task_text(meta)))
                self.check("fight", size, t, "♥")

    def test_commands_output(self):
        """Printed text may wrap like any command's output; it must not crash at any size."""
        from bashou import cli
        for size in SIZES:
            with self.at(size) as (cols, rows):
                for name, function in (("help", cli.print_help), ("level", cli.level), ("pets", cli.pets),
                                       ("achievements", cli.achievements_list), ("stats", cli.stats)):
                    t = Term(cols, rows, flow=True)
                    t.write(printed(function))
                    self.check(name, size, t)

    def test_every_command_in_a_tiny_window(self):
        """Owner: each command, in a very small window, either says the window is too small or prints
        nothing wider than it (a wider line wraps, and a drawing or a QR code comes out broken)."""
        visible = {c.name for c in cli.COMMANDS if not c.hidden}
        self.assertEqual(visible - NOT_RUN, set(RUNS), "a new command: add how to run it to RUNS")
        cols, rows = TINY
        for name, argv in RUNS.items():
            with self.subTest(command=name):
                out, keys = io.StringIO(), io.StringIO("")            # a terminal where Enter is never pressed
                out.isatty = keys.isatty = lambda: True
                with mock.patch("os.get_terminal_size", return_value=os.terminal_size(TINY)), \
                        mock.patch.dict(os.environ, {"HOME": self.tmp.name, "COLUMNS": str(cols), "LINES": str(rows)}), \
                        mock.patch("sys.argv", ["bashou", *argv]), mock.patch("sys.stdin", keys), \
                        contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                    try:
                        cli.main()
                    except SystemExit:
                        pass
                text = out.getvalue()
                if "Your terminal is too small" in text:
                    continue
                lines = screenshot.render.strip(text).split("\n")
                t = Term(cols, max(rows, len(lines) + 1), flow=True)  # the whole output, to look at
                t.write(text)
                self.check(name, "tiny", t)
                cut = [line for line in lines if screenshot.render.width(line.rstrip()[:last_drawn(line)]) > cols]
                self.assertEqual(cut[:3], [], f"bashou {name}: a drawing wider than {cols} columns")


class TooSmallTest(unittest.TestCase):
    """Owner: in a very small window, a command whose screen can't fit says so and stops, instead of
    drawing a broken screen (an evolution looked stuck)."""

    def run_at(self, name, cols, rows, tty=True):
        out = io.StringIO()
        out.isatty = lambda: tty
        with mock.patch("os.get_terminal_size", return_value=os.terminal_size((cols, rows))), \
                mock.patch("sys.stdin.isatty", return_value=tty), contextlib.redirect_stdout(out), \
                mock.patch.dict(os.environ, {"BASHOU_LANG": "en"}):
            stops = cli.too_small(next(c for c in cli.COMMANDS if c.name == name))
        return stops, out.getvalue()

    def test_a_small_window_stops_the_command(self):
        for name, (cols, rows) in SMALLEST.items():
            for small in ((cols - 1, rows), (cols, rows - 1)):
                stops, text = self.run_at(name, *small)
                self.assertTrue(stops, f"{name} at {small}")
                self.assertIn(f"{small[0]}×{small[1]}", text)
                self.assertIn(f"`bashou {name}` needs at least {cols}×{rows}", text)
            self.assertEqual(self.run_at(name, cols, rows), (False, ""), name)

    def test_only_screens_and_only_in_a_terminal(self):
        self.assertEqual(self.run_at("pets", 10, 5), (False, ""))                  # plain text: it wraps
        self.assertEqual(self.run_at("adventure", 10, 5, tty=False), (False, ""))  # piped: no screen drawn
        self.assertEqual(set(SMALLEST), {"evolve", "swap", "lesson", "adventure", "start", "share", "spot"})

if __name__ == "__main__":
    unittest.main()
