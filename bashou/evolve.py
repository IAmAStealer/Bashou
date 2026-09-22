"""`bashou evolve`: watch your pets evolve. Evolutions wait in the save (progress.evolve) and the
pet keeps its old look until you watch them. `s` skips an animation.
"""

import select
import sys
import termios
import time
import tty

from . import creatures, progress, render, state
from .behavior import ACTIONS
from .i18n import _

ESC = "\x1b"
BOLD, DIM, RESET = f"{ESC}[1m", f"{ESC}[2m", f"{ESC}[0m"
SPARKLE = f"{ESC}[38;2;255;220;120m"
WHITE = (235, 235, 245)


def glow(pet):
    """The pet as a white shape: you can't tell yet what it becomes."""
    return creatures.Pet(pet.id, pet.name, pet.base, {k: WHITE for k in pet.palette}, stages=pet.stages)


def scenes(s, e):
    """(title, sprite lines, text, seconds) for one evolution, from the old form to the new one."""
    who = e["who"]
    (old_id, old_name), (new_id, new_name) = (progress.sprite_of(s, who, e[k]) for k in ("from", "to"))
    old, new = creatures.get(old_id), creatures.get(new_id)
    cells = [[True] * max(old.width, new.width) for _ in range(len(old.base) // 2)]

    def draw(pet, form):
        return render.lines(pet, [], cells, form)

    title = _("What? {name} is evolving!").format(name=old_name)
    out = [(title, draw(old, e["from"]), "", 1.2)]
    pause = 0.4
    while pause > 0.07:                                      # old and new shapes, faster and faster
        out += [(title, draw(glow(old), e["from"]), "", pause), (title, draw(glow(new), e["to"]), "", pause)]
        pause *= 0.78
    out.append((title, draw(glow(new), e["to"]), "", 0.5))
    done = _("{old} evolved into {new}!").format(old=old_name, new=f"{BOLD}{new_name}{RESET}")
    learns = DIM + _("New: {actions}").format(actions=_(ACTIONS[e["to"]])) + RESET
    for spark in ("  ✦", " ✧  ✦", "✦  ✧  ✦"):
        out.append((f"{SPARKLE}{spark}{RESET}", draw(new, e["to"]), f"{done}\n  {learns}", 0.35))
    return out


def play(s, e, show, wait):
    """Play one evolution. `show(title, lines, text)` draws a frame, `wait(seconds)` returns the key
    pressed meanwhile (or None). Returns False if the player quit."""
    frames = scenes(s, e)
    for i, (title, lines, text, seconds) in enumerate(frames):
        show(title, lines, text)
        key = wait(seconds)
        if key in ("s", "S") and i < len(frames) - 1:        # skip: straight to the new form
            show(*frames[-1][:3])
            return True
        if key in ("q", "\x03", "\x1b"):
            show(*frames[-1][:3])
            return False
    return True


class Screen:
    """Draws frames in place, below the prompt, and reads keys without waiting for Enter."""
    HEIGHT = 11                                              # title, blank, 6 sprite lines, blank, 2 text lines

    def __init__(self):
        self.drawn = False

    def show(self, title, lines, text):
        rows = [title, ""] + lines + [""] + (text.split("\n") + ["", ""])[:2]
        up = f"{ESC}[{self.HEIGHT}A" if self.drawn else ""
        sys.stdout.write(up + "".join(f"\r{ESC}[K  {row}\n" for row in rows))
        sys.stdout.flush()
        self.drawn = True

    @staticmethod
    def wait(seconds):
        ready, _, _ = select.select([sys.stdin], [], [], seconds)
        return sys.stdin.read(1) if ready else None


def main():
    s = state.load()
    queue = list(s.get("evolving", []))
    if not queue:
        print("  " + _("No evolution waiting. Keep learning, it will come!"))
        return 0
    if not sys.stdin.isatty():
        for e in queue:
            print("  ✨ " + _("{old} evolved into {new}!").format(
                old=progress.sprite_of(s, e["who"], e["from"])[1], new=progress.sprite_of(s, e["who"], e["to"])[1]))
    else:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        sys.stdout.write(f"{ESC}[?25l")
        print("  " + DIM + _("s: skip") + RESET)
        try:
            tty.setcbreak(fd)
            for i, e in enumerate(queue):
                print()
                screen = Screen()
                going = play(s, e, screen.show, screen.wait)
                with state.locked() as saved:
                    progress.watched(saved, e["who"])
                if not going:
                    break
                if i < len(queue) - 1:
                    time.sleep(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
            sys.stdout.write(f"{ESC}[?25h")
        print("  " + DIM + _("Miss the old look? `bashou swap`, then f switches between the forms you reached.") + RESET)
        return 0
    with state.locked() as saved:
        for e in queue:
            progress.watched(saved, e["who"])
    return 0
