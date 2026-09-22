"""Screenshots for the README, as SVG: python3 tools/screenshot.py [out_dir]

A tiny terminal emulator (cursor moves, 24-bit colors, half blocks) is fed Bashou's real drawing code
and real command output, so the pictures show what players see. Writes prompt.svg, duel.svg, pets.svg.
"""

import contextlib
import io
import json
import random
import re
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bashou import challenges, creatures, duel, fight, learn, render, state  # noqa: E402

CW, CH = 9, 18                                   # one terminal cell, in pixels
BG, FG = (24, 24, 30), (215, 215, 220)
DIM = (130, 130, 140)
BASIC = {31: (240, 110, 110), 32: (130, 210, 120), 33: (240, 200, 90), 34: (120, 160, 240),
         35: (200, 140, 230), 36: (110, 200, 210), 37: FG}
CSI = re.compile(r"\x1b\[([0-9;]*)([A-Za-z])|\x1b([78])")


class Screen:
    def __init__(self, cols, rows):
        self.cols, self.rows = cols, rows
        self.cells = [[(" ", None, None, False) for _ in range(cols)] for _ in range(rows)]
        self.r = self.c = 0
        self.saved = (0, 0)
        self.fg = self.bg = None
        self.bold = self.dim = False

    def put(self, ch):
        if ch == "\n":
            self.r, self.c = self.r + 1, 0
            return
        if 0 <= self.r < self.rows and 0 <= self.c < self.cols:
            fg = DIM if self.dim and not self.fg else self.fg
            self.cells[self.r][self.c] = (ch, fg, self.bg, self.bold)
            if render.width(ch) == 2 and self.c + 1 < self.cols:
                self.cells[self.r][self.c + 1] = ("", None, self.bg, False)
        self.c += render.width(ch)

    def sgr(self, params):
        codes = [int(p) for p in params.split(";") if p] or [0]
        i = 0
        while i < len(codes):
            n = codes[i]
            if n == 0:
                self.fg = self.bg = None
                self.bold = self.dim = False
            elif n == 1:
                self.bold = True
            elif n == 2:
                self.dim = True
            elif n in (38, 48) and codes[i + 1] == 2:
                rgb = tuple(codes[i + 2:i + 5])
                if n == 38:
                    self.fg = rgb
                else:
                    self.bg = rgb
                i += 4
            elif n in BASIC:
                self.fg = BASIC[n]
            i += 1

    def write(self, text):
        pos = 0
        for m in CSI.finditer(text):
            for ch in text[pos:m.start()]:
                self.put(ch)
            pos = m.end()
            params, cmd, esc = m.groups()
            if esc == "7":
                self.saved = (self.r, self.c)
            elif esc == "8":
                self.r, self.c = self.saved
            elif cmd == "H":
                r, _, c = (params or "1;1").partition(";")
                self.r, self.c = int(r or 1) - 1, int(c or 1) - 1
            elif cmd == "C":
                self.c += int(params or 1)
            elif cmd == "m":
                self.sgr(params)
            elif cmd == "J":
                self.cells = [[(" ", None, None, False) for _ in range(self.cols)] for _ in range(self.rows)]
        for ch in text[pos:]:
            self.put(ch)

    def svg(self, title):
        pad, bar = 14, 30
        w, h = self.cols * CW + 2 * pad, self.rows * CH + 2 * pad + bar
        hexc = "#%02x%02x%02x".__mod__
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
               f'<title>{title}</title>',
               f'<rect width="{w}" height="{h}" rx="10" fill="{hexc(BG)}"/>',
               f'<rect width="{w}" height="{bar}" rx="10" fill="#33333d"/>',
               f'<rect y="{bar - 10}" width="{w}" height="10" fill="#33333d"/>']
        for i, color in enumerate(("#ff5f57", "#febc2e", "#28c840")):
            out.append(f'<circle cx="{18 + i * 20}" cy="{bar // 2}" r="6" fill="{color}"/>')
        out.append(f'<text x="{w // 2}" y="{bar // 2 + 5}" fill="#b0b0b8" font-family="sans-serif" '
                   f'font-size="13" text-anchor="middle">{title}</text>')
        out.append('<g shape-rendering="crispEdges">')
        texts = []
        for r, row in enumerate(self.cells):
            y = bar + pad + r * CH
            for c, (ch, fg, bg, bold) in enumerate(row):
                x = pad + c * CW
                if bg:
                    out.append(f'<rect x="{x}" y="{y}" width="{CW}" height="{CH}" fill="{hexc(bg)}"/>')
                if ch == "▀":
                    out.append(f'<rect x="{x}" y="{y}" width="{CW}" height="{CH // 2}" fill="{hexc(fg or FG)}"/>')
                elif ch == "▄":
                    out.append(f'<rect x="{x}" y="{y + CH // 2}" width="{CW}" height="{CH // 2}" fill="{hexc(fg or FG)}"/>')
                elif ch.strip():
                    texts.append((x, y, ch, fg or FG, bold))
        out.append("</g>")
        out.append('<g font-family="DejaVu Sans Mono, Menlo, Consolas, monospace" font-size="15">')
        for x, y, ch, fg, bold in texts:
            ch = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}.get(ch, ch)
            weight = ' font-weight="bold"' if bold else ""
            out.append(f'<text x="{x}" y="{y + 14}" fill="{hexc(fg)}"{weight}>{ch}</text>')
        out.append("</g></svg>")
        return "\n".join(out) + "\n"


def sprite(pet, poses=()):
    return render.lines(pet, list(poses), [[True] * pet.width for _ in range(len(pet.base) // 2)])


def draw_pet(screen, pet, bubble=None):
    """The pet at the top right with its speech bubble, as the companion draws them."""
    x = screen.cols - pet.width + 1
    screen.write("".join(f"\x1b[{i + 1};{x}H{line}" for i, line in enumerate(sprite(pet))))
    if bubble:
        lines, bw = render.bubble(bubble, x - 2)
        screen.write("".join(f"\x1b[{i + 1};{x - bw}H\x1b[38;2;150;190;230m{line}\x1b[0m"
                             for i, line in enumerate(lines)))


PROMPT = "\x1b[38;2;130;210;120mme@laptop\x1b[0m:\x1b[38;2;120;160;240m~/notes\x1b[0m$ "


def prompt_shot():
    s = Screen(92, 21)
    draw_pet(s, creatures.get("stardust"), "Ctrl+R searches your history as you type.")
    s.write("\x1b[8;1H")
    s.write(PROMPT + "grep -c ERROR app.log\n3\n")
    s.write(PROMPT + "tar -czf backup.tgz notes/\n")
    s.write(PROMPT + "bashou learn tar -czf backup.tgz notes/\n")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        learn.main(["tar", "-czf", "backup.tgz", "notes/"])
    s.write(out.getvalue().strip("\n") + "\n\n")
    s.write(PROMPT)
    return s.svg("Bashou: your pet lives in the corner of the terminal")


def duel_shot():
    s = Screen(92, 21)
    ch = challenges.BY_ID["grep_hydra"]
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "arena").mkdir()
        meta = {"challenge": ch.id, "hints": 0, **ch.setup(base / "arena", random.Random(3))}
        (base / "meta.json").write_text(json.dumps(meta))
        (base / "duel.json").write_text(json.dumps({"hearts": 2, "enemy": 2, "offset": 0, "event": "hit", "at": 0,
                                                    "said": "💥 grep hits the Log Hydra!"}))
        fake = {**state.default(), "starter": "star"}                    # no spoiler: the first form
        with mock.patch.object(state, "load", return_value=fake):
            scene = duel.Scene(base, 0)
        body, _erase = scene.frame(s.cols + 1, 1.0)
        s.write(body)
        s.write(f"\x1b[{scene.height() + 2};1H")
        s.write(fight.banner(ch, ch.task_text(meta)).strip("\n").split("\n\n")[0] + "\n\n")
        arena = "\x1b[38;2;240;110;110m⚔ arena\x1b[0m arena $ "
        s.write(arena + "awk '/ERROR/' app.log | wc -l\n7\n")
        s.write(arena + "grep -cF '[ERROR]' app.log\n4\n")
        s.write(arena + "answer 4\n")
        s.write(f"\n\x1b[38;2;130;210;120m\x1b[1m✨ You beat the Log Hydra!\x1b[0m\n")
    return s.svg("bashou fight: beat threats with real commands")


def pets_shot():
    """The three starters you choose from, then pets to discover: silhouettes only, as on the board."""
    from bashou.board import silhouette
    shown = [(creatures.get(forms[0]), creatures.FORM_NAMES[forms[0]]) for forms in creatures.STARTERS.values()]
    hidden = [(silhouette(creatures.get(creatures.form(p, 1))), "???") for p in ("fox", "octopus", "bat")]
    per_row = 6
    s = Screen(per_row * 19 + 1, 8)
    for i, (pet, name) in enumerate(shown + hidden):
        c = i * 19 + 2
        s.write("".join(f"\x1b[{1 + j};{c}H{line}" for j, line in enumerate(sprite(pet))))
        s.write(f"\x1b[7;{c + (17 - len(name)) // 2}H\x1b[2m{name}\x1b[0m")
    return s.svg("Choose a starter, then discover 25 pets")


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "doc" / "img"
    out.mkdir(parents=True, exist_ok=True)
    for name, shot in (("prompt", prompt_shot), ("duel", duel_shot), ("pets", pets_shot)):
        (out / f"{name}.svg").write_text(shot())
        print(out / f"{name}.svg")


if __name__ == "__main__":
    main()
