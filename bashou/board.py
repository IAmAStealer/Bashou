"""`bashou swap`: a 4×4 board to pick your active pet, with a live preview."""

import os
import select
import sys
import termios
import tty

from . import achievements, creatures, progress, render, state
from .behavior import ACTIONS
from .creatures import FORM_NAMES, ROSTER, STAGES, STARTERS
from .i18n import _

ESC = "\x1b"
COLS = 4
TILE_W, TILE_H = 16, 3
DIM, BOLD, RESET, REV = f"{ESC}[2m", f"{ESC}[1m", f"{ESC}[0m", f"{ESC}[7m"
ACCENT = f"{ESC}[38;2;150;190;230m"
KEYS = {"\x1b[A": "up", "\x1b[B": "down", "\x1b[C": "right", "\x1b[D": "left",
        "k": "up", "j": "down", "l": "right", "h": "left", "\r": "enter", "\n": "enter",
        "q": "quit", "\x1b": "quit", "\x04": "quit", "\x03": "quit"}


def hint(s, pet):
    if pet in progress.STATE_PETS:
        return _(progress.STATE_PETS[pet][1])
    if pet in progress.CONSTRUCT_PETS:
        construct, needed = progress.CONSTRUCT_PETS[pet]
        return f"{s['constructs'].get(construct, 0)}/{needed} × " + _(progress.CONSTRUCT_NAMES[construct])
    for count, p in progress.MILESTONES:
        if p == pet:
            return _("{count} commands").format(count=f"{s['commands']:,}/{count:,}")
    if pet in progress.TOOL_PETS:
        tools, needed = progress.TOOL_PETS[pet]
        return f"{progress.tool_uses(s, tools)}/{needed} × {min(tools)}"
    return ""


def silhouette(pet):
    return creatures.Pet(pet.id, pet.name, pet.base, {k: (70, 72, 86) for k in pet.palette},
                         stages=pet.stages)


class Board:
    def __init__(self):
        self.s = state.load()
        ids = ["starter"] + [pet for pet, rule in ROSTER]   # starter on its own row, then the 4×4 grid
        self.ids = ids
        self.pos = ids.index(self.s["active"]) if self.s["active"] in ids else 0
        self.breath = False
        self.message = ""

    def rows(self):
        return -(-(len(self.ids) - 1) // COLS)          # the last row may be partly empty

    def tile(self, i):
        if i >= len(self.ids):
            return ["", "", ""]
        pet = self.ids[i]
        unlocked = pet in self.s["pets"] or pet == "starter"
        if pet == "starter":
            lvl = progress.starter_level(self.s)
            name = progress.current(self.s, "starter")[2]
            top = _("Lv {level}").format(level=lvl) + ("  ●" if self.s["active"] == "starter" else "")
        elif unlocked:
            st = progress.stage(self.s, pet)
            name = _(STAGES[pet][st - 1])
            top = "★" * st + "☆" * (3 - st) + ("  ●" if pet == self.s["active"] else "")
        else:
            name, top = "???", "☆☆☆"
        name = name[:TILE_W - 2]
        style = REV if i == self.pos else ("" if unlocked else DIM)
        return [f"{style} {top:<{TILE_W - 2}} {RESET}",
                f"{style} {name:<{TILE_W - 2}} {RESET}",
                ""]

    def starter_preview(self):
        s = self.s
        sprite, form, name, voice = progress.current(s, "starter")
        pet = creatures.get(sprite)
        cells = [[True] * pet.width for _ in range(len(pet.base) // 2)]
        out = render.lines(pet, ["inhale"] if self.breath else [], cells) + [""]
        lvl = progress.starter_level(s)
        out.append(f"{BOLD}{name}{RESET}  " + _("level {level}").format(level=f"{lvl}/{progress.MAX_LEVEL}"))
        if lvl < progress.MAX_LEVEL:
            per = progress.ACHIEVEMENTS_PER_LEVEL
            out.append(DIM + _("{n} achievement(s) to level {level}").format(
                n=per - len(s["achievements"]) % per, level=lvl + 1) + RESET)
        forms = STARTERS[s["starter"] or "cat"]
        out.append(DIM + " → ".join(_(FORM_NAMES[f]) for f in forms) + "  "
                   + _("(shape changes at levels 4 and 7)") + RESET)
        return out

    def preview(self):
        pet_id = self.ids[self.pos]
        if pet_id == "starter":
            return self.starter_preview()
        unlocked = pet_id in self.s["pets"]
        drawn = pet_id in creatures.PETS
        out = []
        if drawn:
            pet = creatures.PETS[pet_id]
            shown = pet if unlocked else silhouette(pet)
            stage = progress.stage(self.s, pet_id) if unlocked else 1
            cells = [[True] * pet.width for _ in range(len(pet.base) // 2)]
            poses = ["inhale"] if self.breath else []
            out += render.lines(shown, poses, cells, stage)
        else:
            out += ["", "", f"{DIM}   " + _("(art coming soon)") + RESET, "", "", ""]
        out.append("")
        if unlocked:
            st = progress.stage(self.s, pet_id)
            out.append(f"{BOLD}{_(STAGES[pet_id][st - 1])}{RESET}  {'★' * st}{'☆' * (3 - st)}")
            if st < 3:
                out.append(DIM + _("next: {name}, learns to {actions}").format(
                    name=_(STAGES[pet_id][st]), actions=_(ACTIONS[st + 1])) + RESET)
        else:
            out.append(f"{BOLD}???{RESET}")
            out.append(ACCENT + _("unlock: {how}").format(how=hint(self.s, pet_id)) + RESET)
        fam = achievements.family(pet_id)
        earned = set(self.s["achievements"])
        out.append("")
        for a in fam:
            mark = "🏆" if a.id in earned else "· "
            out.append(f"{mark} {_(a.name)}" if a.id in earned else f"{DIM}{mark} {_(a.name)}: {_(a.how)}{RESET}")
        return out

    def draw(self):
        cols = os.get_terminal_size().columns
        grid = [f"{BOLD}Bashou{RESET} {DIM}· " + _("{n} pets · arrows/hjkl · Enter: pick · q: quit").format(
            n=f"{len(self.s['pets'])}/{len(self.ids)}") + RESET, ""]
        grid += self.tile(0)
        for row in range(self.rows()):
            tiles = [self.tile(1 + row * COLS + c) for c in range(COLS)]
            for line in range(TILE_H):
                grid.append("".join(t[line] if t[line] else " " * TILE_W for t in tiles))
        grid.append(self.message)
        preview = self.preview()
        out = [f"{ESC}[H{ESC}[2J"]
        side = cols >= COLS * TILE_W + 40
        for i, line in enumerate(grid):
            out.append(f"{ESC}[{i + 1};1H{line}")
        for i, line in enumerate(preview):
            if side:
                out.append(f"{ESC}[{i + 3};{COLS * TILE_W + 4}H{line}")
            else:
                out.append(f"{ESC}[{len(grid) + i + 2};2H{line}")
        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def key(self, k):
        n, size = self.pos, len(self.ids)
        last_row = 1 + (self.rows() - 1) * COLS
        if k == "up":
            self.pos = 0 if 1 <= n <= COLS else (n - COLS if n else last_row)
        elif k == "down":
            if n == 0:
                self.pos = 1
            elif n + COLS < size:
                self.pos = n + COLS
            else:                                        # into the partial last row, or back to the starter
                self.pos = size - 1 if n < last_row else 0
        elif k == "left":
            self.pos = (n - 1) % size
        elif k == "right":
            self.pos = (n + 1) % size
        elif k == "enter":
            pet = self.ids[n]
            if pet != "starter" and pet not in self.s["pets"]:
                self.message = DIM + _("Not unlocked yet: {how}").format(how=hint(self.s, pet)) + RESET
                return True
            with state.locked() as s:
                s["active"] = pet
            self.s = state.load()
            return False
        elif k == "quit":
            return False
        self.message = ""
        return True

    def run(self):
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        sys.stdout.write(f"{ESC}[?1049h{ESC}[?25l")
        try:
            tty.setcbreak(fd)
            running = True
            while running:
                self.draw()
                ready = select.select([fd], [], [], 1.5)[0]
                if not ready:
                    self.breath = not self.breath
                    continue
                data = os.read(fd, 8).decode(errors="ignore")
                running = self.key(KEYS.get(data, ""))
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
            sys.stdout.write(f"{ESC}[?25h{ESC}[?1049l")
            sys.stdout.flush()
        print("  " + _("{name} is your pet.").format(name=progress.current(self.s)[2]))


def main():
    Board().run()
