"""`bashou adventure`: your starter walks into the world, seen from behind."""

import os
import select
import sys
import termios
import time
import tty

from .. import progress, state
from ..i18n import _
from . import canvas, scene, sprites

ESC = "\x1b"
FPS = 15
SPEED = 5.0                    # world units per second while walking
QUIT_KEYS = ("s", "S", "q", "Q", ESC, "\x03", "\x04")
BIOME_ORDER = ["meadow", "hills", "forest", "sand", "water", "dungeon"]
BIOME_LENGTH = 60


def default():
    return {"distance": 0.0}


def load():
    return {**default(), **(state.load().get("adventure") or {})}


def save(adv):
    with state.locked() as s:
        s["adventure"] = adv


def biome_name(biome):
    return {"meadow": _("Meadow"), "hills": _("Hills"), "forest": _("Forest"), "sand": _("Desert"),
            "water": _("Lake"), "dungeon": _("Dungeon")}[biome]


def biome_at(distance):
    return BIOME_ORDER[int(distance // BIOME_LENGTH) % len(BIOME_ORDER)]


class Game:
    def __init__(self, cols, rows):
        self.adv = load()
        s = state.load()
        self.frames, self.palette = sprites.hero(progress.current(s, "starter")[0])
        self.walk_until = 0.0
        self.auto = False
        self.quit = False
        self.resize(cols, rows)

    def resize(self, cols, rows):
        self.cols, self.rows = cols, rows
        self.canvas = canvas.Canvas(cols, (rows - 1) * 2)
        self.scale = 2 if self.canvas.h >= 40 else 1

    def key(self, k, now):
        if k in QUIT_KEYS:
            self.quit = True
        elif k in ("\x1b[A", "w", "W", "k"):
            self.walk_until = now + 0.3            # key repeat keeps it going while held
        elif k == " ":
            self.auto = not self.auto

    def walking(self, now):
        return self.auto or now < self.walk_until

    def update(self, dt, now):
        if self.walking(now):
            self.adv["distance"] += SPEED * dt

    def draw(self, t):
        c = self.canvas
        d = self.adv["distance"]
        scene.draw(c, biome_at(d), d, t)
        step = int(d * 1.5) % len(self.frames) if self.walking(time.time()) else 0
        w, h = 17 * self.scale, 12 * self.scale
        c.sprite(self.frames[step], self.palette, (c.w - w) // 2, c.h - h - 1, self.scale)
        return c.render()

    def hud(self):
        d = self.adv["distance"]
        text = (f" {biome_name(biome_at(d))} · {int(d)} m   "
                + _("↑ walk · space: auto-walk · s: save & quit"))
        return f"{ESC}[{self.rows};1H{ESC}[0m{ESC}[2K{text[:self.cols - 1]}"


def main():
    if not sys.stdin.isatty():
        print(_("The adventure needs a terminal."))
        return 1
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    size = os.get_terminal_size()
    if size.columns < 40 or size.lines < 16:
        print(_("Make the terminal a bit bigger for the adventure (40×16 at least)."))
        return 1
    game = Game(size.columns, size.lines)
    out = sys.stdout
    out.write(f"{ESC}[?1049h{ESC}[?25l{ESC}[2J")
    start = last = time.time()
    try:
        tty.setcbreak(fd)
        while not game.quit:
            now = time.time()
            size = os.get_terminal_size()
            if (size.columns, size.lines) != (game.cols, game.rows):
                game.resize(size.columns, size.lines)
                out.write(f"{ESC}[2J")
            game.update(now - last, now)
            last = now
            out.write(game.draw(now - start) + game.hud())
            out.flush()
            if select.select([fd], [], [], 1 / FPS)[0]:
                data = os.read(fd, 32).decode(errors="ignore")
                for k in split_keys(data):
                    game.key(k, now)
    except KeyboardInterrupt:
        pass
    finally:
        save(game.adv)
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        out.write(f"{ESC}[0m{ESC}[?25h{ESC}[?1049l")
        out.flush()
    print("  " + _("Adventure saved ({m} m walked). Come back with: bashou adventure").format(
        m=int(game.adv["distance"])))
    return 0


def split_keys(data):
    """Split a read into keys: arrow escapes stay whole."""
    keys, i = [], 0
    while i < len(data):
        if data[i] == ESC and data[i + 1:i + 2] == "[" and i + 2 < len(data):
            keys.append(data[i:i + 3])
            i += 3
        else:
            keys.append(data[i])
            i += 1
    return keys
