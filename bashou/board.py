"""`bashou swap`: a 4×4 board to pick your active pet, with a live preview."""

import os
import select
import sys
import termios
import tty

from . import achievements, creatures, progress, render, state
from .behavior import ACTIONS
from .creatures import ROSTER, STAGES

ESC = "\x1b"
COLS = 4
TILE_W, TILE_H = 16, 3
DIM, BOLD, RESET, REV = f"{ESC}[2m", f"{ESC}[1m", f"{ESC}[0m", f"{ESC}[7m"
ACCENT = f"{ESC}[38;2;150;190;230m"
KEYS = {"\x1b[A": "up", "\x1b[B": "down", "\x1b[C": "right", "\x1b[D": "left",
        "k": "up", "j": "down", "l": "right", "h": "left", "\r": "enter", "\n": "enter",
        "q": "quit", "\x1b": "quit"}


def hint(s, pet):
    for count, p in progress.MILESTONES:
        if p == pet:
            return f"{s['commands']:,}/{count:,} commands"
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
        ids = [pet for pet, _ in ROSTER]
        self.ids = ids
        self.pos = ids.index(self.s["active"]) if self.s["active"] in ids else 0
        self.breath = False
        self.message = ""

    def tile(self, i):
        pet = self.ids[i]
        unlocked = pet in self.s["pets"]
        if unlocked:
            st = progress.stage(self.s, pet)
            name = STAGES[pet][st - 1]
            top = "★" * st + "☆" * (3 - st) + ("  ●" if pet == self.s["active"] else "")
        else:
            name, top = "???", "☆☆☆"
        name = name[:TILE_W - 2]
        style = REV if i == self.pos else ("" if unlocked else DIM)
        return [f"{style} {top:<{TILE_W - 2}} {RESET}",
                f"{style} {name:<{TILE_W - 2}} {RESET}",
                ""]

    def preview(self):
        pet_id = self.ids[self.pos]
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
            out += ["", "", f"{DIM}   (art coming soon){RESET}", "", "", ""]
        out.append("")
        if unlocked:
            st = progress.stage(self.s, pet_id)
            out.append(f"{BOLD}{STAGES[pet_id][st - 1]}{RESET}  {'★' * st}{'☆' * (3 - st)}")
            if st < 3:
                out.append(f"{DIM}next: {STAGES[pet_id][st]}, learns to {ACTIONS[st + 1]}{RESET}")
        else:
            out.append(f"{BOLD}???{RESET}")
            out.append(f"{ACCENT}unlock: {hint(self.s, pet_id)}{RESET}")
        fam = achievements.family(pet_id)
        earned = set(self.s["achievements"])
        out.append("")
        for a in fam:
            mark = "🏆" if a.id in earned else "· "
            out.append(f"{mark} {a.name}" if a.id in earned else f"{DIM}{mark} {a.name}: {a.how}{RESET}")
        return out

    def draw(self):
        cols = os.get_terminal_size().columns
        grid = [f"{BOLD}Bashou{RESET} {DIM}· {len(self.s['pets'])}/{len(self.ids)} pets · "
                f"arrows/hjkl · Enter: pick · q: quit{RESET}", ""]
        for row in range(len(self.ids) // COLS):
            tiles = [self.tile(row * COLS + c) for c in range(COLS)]
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
        if k == "up":
            self.pos = (n - COLS) % size
        elif k == "down":
            self.pos = (n + COLS) % size
        elif k == "left":
            self.pos = (n - 1) % size
        elif k == "right":
            self.pos = (n + 1) % size
        elif k == "enter":
            pet = self.ids[n]
            if pet not in self.s["pets"]:
                self.message = f"{DIM}Not unlocked yet: {hint(self.s, pet)}{RESET}"
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
                ready, _, _ = select.select([fd], [], [], 1.5)
                if not ready:
                    self.breath = not self.breath
                    continue
                data = os.read(fd, 8).decode(errors="ignore")
                running = self.key(KEYS.get(data, ""))
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
            sys.stdout.write(f"{ESC}[?25h{ESC}[?1049l")
            sys.stdout.flush()
        pet = self.s["active"]
        print(f"  {STAGES[pet][progress.stage(self.s, pet) - 1]} is your pet.")


def main():
    Board().run()
