"""`bashou swap`: a 4×4 board to pick your active pet, with a live preview."""

import os
import sys

from . import achievements, creatures, progress, render, state, terminal
from .behavior import ACTIONS
from .creatures import STARTERS, roster
from .i18n import _
from .render import ESC, BOLD, DIM, RESET, REV, ACCENT

COLS = 4
TILE_W, TILE_H = 18, 2          # 16-character names (Golem de cristal) fit; 4 × 18 fits 80 columns
SHOWN = f"{ESC}[38;2;245;200;70m"  # gold: the stars of the form shown
SPRITE_W = 19                     # the sprite and a gap: the forms list starts after it
HOVER = f"{ESC}[48;2;55;60;82m"   # the tile under the mouse
PREVIEW_SHORT = 9                  # sprite, blank line, name and next stage
KEYS = {"f": "form"}             # besides terminal.NAMES


def hint(s, pet):
    return progress.how_to_unlock(s, pet)


def silhouette(pet):
    return creatures.Pet(pet.id, pet.name, pet.base, {k: (70, 72, 86) for k in pet.palette},
                         stages=pet.stages)


class Board:
    def __init__(self):
        self.s = state.load()
        ids = ["starter"]                 # starter on its own row, then the 4×4 grid
        self.ponies = []                  # the ponies found: one tile for them all (owner, 2026-10-16)
        for pet, rule in roster(self.s):
            if creatures.FAMILIES[pet].herd:
                if not self.ponies:
                    ids.append("ponies")
                self.ponies.append(pet)
            else:
                ids.append(pet)
        self.ids = ids
        active = self.s["active"]
        self.pony = active if active in self.ponies else (self.ponies[0] if self.ponies else None)
        active = "ponies" if active in self.ponies else active
        self.pos = ids.index(active) if active in ids else 0
        self.breath = False
        self.message = ""
        self.top = 0                      # first pet row shown when the grid scrolls
        self.cols = COLS                  # tiles per row: fewer on a narrow (portrait) terminal
        self.hover = None                 # the tile under the mouse
        self.last_frame = ""              # what's on screen: an unchanged frame isn't sent again
        self.hits = []                    # (row, first column, last column, ("tile", i) or ("form", k)): what a click hits
        self.form_lines = {}              # preview line -> (form number, column in the line) of the forms list

    def rows(self):
        return -(-(len(self.ids) - 1) // self.cols)     # the last row may be partly empty

    def tile(self, i):
        if i >= len(self.ids):
            return ["", ""]
        pet = self.ids[i]
        unlocked = pet in self.s["pets"] or pet in ("starter", "ponies")
        if pet == "ponies":
            from .pony import herd
            name = _("Ponies")
            top = f"🐴 {len(self.ponies)}/{len(herd())}" + ("  ●" if self.s["active"] in self.ponies else "")
        elif pet == "starter":
            lvl = progress.starter_level(self.s)
            name = progress.current(self.s, "starter")[2]
            top = _("Lv {level}").format(level=lvl) + ("  ●" if self.s["active"] == "starter" else "")
        elif unlocked:
            name = progress.current(self.s, pet)[2]
            top = progress.stars(self.s, pet) + ("  ●" if pet == self.s["active"] else "")
        else:
            name, top = "???", "☆☆☆"
        name = name[:TILE_W - 2]
        style = REV if i == self.pos else (HOVER if i == self.hover else "") + ("" if unlocked else DIM)
        return [f"{style} {top:<{TILE_W - 2}} {RESET}",
                f"{style} {name:<{TILE_W - 2}} {RESET}"]

    def forms(self, who):
        """The forms list next to the sprite: "★★ 2. Tree frog ◀" (the one shown), "☆☆☆ 3. ??? (5 achievements)"
        for the next one, "???" after it: forms are to discover (owner), only the reached ones are named."""
        chain, top, shown = progress.chain(self.s, who), progress.reached(self.s, who), progress.look(self.s, who)
        out = []
        for k, sprite in enumerate(chain, 1):
            if k <= top:
                name = _(creatures.PETS[sprite].name) + (" ◀" if k == shown else "")
            else:
                name = "???" + (f" ({self.needs(chain, k)})" if k == top + 1 else "")
            out.append((k, ("★" if k <= top else "☆") * k + f" {k}. {name}"))
        return out

    def needs(self, chain, k):
        """What form k waits for: "level 6", "5 achievements"."""
        need = creatures.PETS[chain[k - 2]].next_at
        return (_("level {level}").format(level=need["level"]) if "level" in need
                else f"{need['achievements']} 🏆")

    def with_forms(self, sprite_lines, who, width):
        """The sprite, and its forms on its right (owner), cut to the room left; under it only when there's
        almost no room. Remembers where each form is, for a click."""
        forms = self.forms(who)
        self.form_lines = {}
        more = progress.reached(self.s, who) > 1                 # another form to show: say how
        if width >= SPRITE_W + 12:
            out = []
            for i in range(max(len(sprite_lines), len(forms))):
                left = sprite_lines[i] if i < len(sprite_lines) else ""
                pad = " " * (SPRITE_W - render.width(render.strip(left)))
                if i < len(forms):
                    k, text = forms[i]
                    self.form_lines[i] = (k, SPRITE_W)
                    text = render.fit(text, width - SPRITE_W)[0]
                    out.append(left + pad + self.colored(text) + RESET)
                elif i == len(forms) and more:
                    out.append(left + pad + ACCENT + _("f: change form") + RESET)
                else:
                    out.append(left)
            if len(forms) >= len(sprite_lines) and more:
                out.append(" " * SPRITE_W + ACCENT + _("f: change form") + RESET)
            return out
        out = list(sprite_lines) + [""]
        for k, text in forms:
            self.form_lines[len(out)] = (k, 0)
            out.append(self.colored(text) + RESET)
        if more:
            out.append(ACCENT + _("f: change form") + RESET)
        return out

    @staticmethod
    def colored(text):
        """The form shown: its stars in gold. Forms not reached: dim."""
        if text.endswith("◀"):
            stars, rest = text.split(" ", 1)
            return SHOWN + stars + RESET + " " + rest
        return (DIM if not text.startswith("★") or "???" in text else "") + text

    def pick_form(self, k):
        """A click on a form: show it, or say what it waits for."""
        who = self.ids[self.pos]
        chain, top = progress.chain(self.s, who), progress.reached(self.s, who)
        if k <= top:
            with state.locked() as s:
                progress.set_look(s, who, k)
            self.s = state.load()
            self.message = _("{name}: form {n}/{total}").format(name=progress.current(self.s, who)[2], n=k, total=top)
            return
        need = creatures.PETS[chain[k - 2]].next_at
        self.message = DIM + (_("Form {n} comes at level {level}.").format(n=k, level=need["level"]) if "level" in need
                              else _("Form {n} comes with {count} achievements of this family.").format(
                                  n=k, count=need["achievements"])) + RESET

    def starter_preview(self, width=60):
        s = self.s
        sprite, form, name, voice = progress.current(s, "starter")
        pet = creatures.get(sprite)
        cells = [[True] * pet.width for _ in range(len(pet.base) // 2)]
        out = self.with_forms(render.lines(pet, ["inhale"] if self.breath else [], cells, progress.look(s, "starter")),
                              "starter", width) + [""]
        lvl = progress.starter_level(s)
        out.append(f"{BOLD}{name}{RESET}  " + _("level {level}").format(level=f"{lvl}/{progress.MAX_LEVEL}"))
        if lvl < progress.MAX_LEVEL:
            per = progress.ACHIEVEMENTS_PER_LEVEL
            out.append(DIM + _("{n} achievement(s) to level {level}").format(
                n=per - len(s["achievements"]) % per, level=lvl + 1) + RESET)
        return out

    def pony_preview(self):
        from . import pony
        pet = creatures.get(creatures.FAMILIES[self.pony].first)
        cells = [[True] * pet.width for _ in range(len(pet.base) // 2)]
        out = render.lines(pet, ["inhale"] if self.breath else [], cells) + [""]
        out.append(f"{BOLD}{_(creatures.NAMES[self.pony])}{RESET}  " + DIM + _("pony {n}/{total} found").format(
            n=self.ponies.index(self.pony) + 1, total=len(self.ponies)) + RESET)
        if len(self.ponies) > 1:
            out.append(ACCENT + _("f: the next pony") + RESET)
        out += [""] + [DIM + line + RESET for line in render.wrap(pony.where().get(self.pony) or _(creatures.FAMILIES[self.pony].tips[0]), 50, 4)]
        return out

    def preview(self, width=60):
        pet_id = self.ids[self.pos]
        self.form_lines = {}
        if pet_id == "starter":
            return self.starter_preview(width)
        if pet_id == "ponies":
            return self.pony_preview()
        unlocked = pet_id in self.s["pets"]
        drawn = creatures.form(pet_id, 1) in creatures.PETS     # the pet id isn't always a sprite (cat: hacker_cat)
        out = []
        if drawn:
            stage = progress.look(self.s, pet_id) if unlocked else 1
            pet = creatures.PETS[creatures.form(pet_id, stage)]
            shown = pet if unlocked else silhouette(pet)
            cells = [[True] * pet.width for _ in range(len(pet.base) // 2)]
            poses = ["inhale"] if self.breath else []
            drawn_lines = render.lines(shown, poses, cells, stage)
            out += self.with_forms(drawn_lines, pet_id, width) if unlocked else drawn_lines
        else:
            out += ["", "", f"{DIM}   " + _("(art coming soon)") + RESET, "", "", ""]
        out.append("")
        if unlocked:
            top, forms = progress.reached(self.s, pet_id), progress.chain(self.s, pet_id)
            out.append(f"{BOLD}{progress.current(self.s, pet_id)[2]}{RESET}  {progress.stars(self.s, pet_id)}")
            if top < len(forms):
                tier = progress.tier(self.s, pet_id, top + 1)
                name = _(creatures.PETS[forms[top]].name)
                out.append(DIM + (_("next: {name}, learns to {actions}").format(name=name, actions=_(ACTIONS[tier]))
                                  if tier > progress.tier(self.s, pet_id, top) else
                                  _("next: {name}").format(name=name)) + RESET)
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

    def layout(self, cols, lines):
        """(grid lines, preview lines, preview on the side?) fitting a cols × lines terminal.
        When it's too short, the preview keeps its sprite and name, and the grid scrolls."""
        self.cols = max(1, min(COLS, (cols - 1) // TILE_W))
        head = render.heading("Bashou", _("{n} pets · arrows/hjkl or mouse · Enter: pick · f: form · q: quit").format(
            n=f"{sum(p in self.s['pets'] for p in self.ids) + bool(self.ponies)}/{len(self.ids) - 1}"), cols) + [""] + self.tile(0)
        side = cols >= self.cols * TILE_W + 40
        width = max(20, (cols - self.cols * TILE_W - 6) if side else cols - 3)
        preview = [part for line in self.preview(width) for part in render.fit(line, width)]
        dim = self.message.startswith(DIM)
        text = self.message.replace(DIM, "").replace(RESET, "")
        message = [(DIM if dim else "") + part + (RESET if dim else "")
                   for part in render.wrap(text, width, 3)] if text else [""]
        fixed = len(head) + len(message)                              # the message wraps on a few lines
        if side:
            room = lines - fixed
        else:
            if fixed + self.rows() * TILE_H + 1 + len(preview) > lines:
                preview = preview[:PREVIEW_SHORT]
            room = lines - fixed - 1 - len(preview)
        shown = max(1, min(self.rows(), room // TILE_H))
        if self.pos:                                                  # keep the selected row in view
            row = (self.pos - 1) // self.cols
            self.top = min(max(self.top, row - shown + 1), row)
        self.top = max(0, min(self.top, self.rows() - shown))
        grid = list(head)
        self.hits = [(len(head) - TILE_H + 1 + line, 1, TILE_W, ("tile", 0)) for line in range(TILE_H)]
        for row in range(self.top, self.top + shown):
            tiles = [self.tile(1 + row * self.cols + c) for c in range(self.cols)]
            for line in range(TILE_H):
                self.hits += [(len(grid) + 1, 1 + c * TILE_W, (c + 1) * TILE_W, ("tile", 1 + row * self.cols + c))
                              for c in range(self.cols) if 1 + row * self.cols + c < len(self.ids)]
                grid.append("".join(t[line] if t[line] else " " * TILE_W for t in tiles))
        more = shown < self.rows()
        grid += message if text else [DIM + _("↑↓ more pets") + RESET if more else ""]
        left = self.cols * TILE_W + 4 if side else 2
        for i, (k, col) in self.form_lines.items():
            row = i + 3 if side else len(grid) + i + 2
            self.hits.append((row, left + col, left + col + 24, ("form", k)))
        return grid, preview, side

    def draw(self):
        """One frame, written over the last one: no clear screen, and nothing sent when nothing changed.
        Clearing on every redraw made the board flicker when the mouse moved (owner: it can hurt people)."""
        size = os.get_terminal_size()
        grid, preview, side = self.layout(size.columns, size.lines)
        rows = {i + 1: [(1, line)] for i, line in enumerate(grid)}
        left = self.cols * TILE_W + 4 if side else 2
        for i, line in enumerate(preview):
            rows.setdefault(i + 3 if side else len(grid) + i + 2, []).append((left, line))
        out = [f"{ESC}[?2026h"]                            # terminals that know it show the frame at once
        for row in range(1, size.lines + 1):               # below the last line the terminal would scroll
            out.append(f"{ESC}[{row};1H{ESC}[K")
            for col, line in rows.get(row, []):
                out.append(f"{ESC}[{row};{col}H{line}{ESC}[K")
        out.append(f"{ESC}[?2026l")
        frame = "".join(out)
        if frame != self.last_frame:
            self.last_frame = frame
            sys.stdout.write(frame)
            sys.stdout.flush()

    def switch_form(self, pet):
        """Show the next form this pet has reached (looks only: it keeps every action)."""
        if pet != "starter" and pet not in self.s["pets"]:
            return
        top = progress.reached(self.s, pet)
        if top == 1:
            self.message = DIM + _("Only one form so far: it evolves with achievements.") + RESET
            return
        form = progress.look(self.s, pet) % top + 1
        with state.locked() as s:
            progress.set_look(s, pet, form)
        self.s = state.load()
        self.message = _("{name}: form {n}/{total}").format(name=progress.current(self.s, pet)[2], n=form, total=top)

    def key(self, k):
        n, size = self.pos, len(self.ids)
        last_row, COLS = 1 + (self.rows() - 1) * self.cols, self.cols
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
            pet = self.pony if self.ids[n] == "ponies" else self.ids[n]
            if pet != "starter" and pet not in self.s["pets"]:
                self.message = DIM + _("Not unlocked yet: {how}").format(how=hint(self.s, pet)) + RESET
                return True
            with state.locked() as s:
                s["active"] = pet
            self.s = state.load()
            return False
        elif k == "form" and self.ids[n] == "ponies":
            self.pony = self.ponies[(self.ponies.index(self.pony) + 1) % len(self.ponies)]
            self.message = ""
            return True
        elif k == "form":
            self.switch_form(self.ids[n])
            return True
        elif k == "quit":
            return False
        self.message = ""
        return True

    def hit(self, x, y):
        return next((target for row, x0, x1, target in self.hits if row == y and x0 <= x <= x1), None)

    def where(self, target, k=None):
        """(column, row) on screen of a pet's tile, or of form k in the list: for tests."""
        want = ("form", k) if target == "form" else ("tile", self.ids.index(target))
        row, x0, x1, _t = next(h for h in self.hits if h[3] == want)
        return x0 + 1, row

    def mouse(self, event):
        """A mouse event (terminal.mouse): hover lights a tile, a click selects it, a second click picks it;
        a click on a form shows it. False when the board is done."""
        kind, x, y = event
        if kind in ("wheel_up", "wheel_down"):
            return self.key("up" if kind == "wheel_up" else "down")
        target = self.hit(x, y)
        if kind == "move":
            self.hover = target[1] if target and target[0] == "tile" else None
            return True
        if not target:
            return True
        if target[0] == "form":
            self.pick_form(target[1])
            return True
        if target[1] == self.pos:
            return self.key("enter")
        self.pos, self.message = target[1], ""
        return True

    def run(self):
        with terminal.Screen(mouse=True) as screen:
            running = True
            while running:
                self.draw()
                keys = screen.keys(1.5)
                if not keys:
                    self.breath = not self.breath
                for k in keys:
                    event = terminal.mouse(k)
                    running = running and (self.mouse(event) if event else self.key(terminal.name(k, KEYS)))
        print("  " + _("{name} is your pet.").format(name=progress.current(self.s)[2]))


def main():
    Board().run()
