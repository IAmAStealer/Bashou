"""The fight, drawn where your pet lives: the task, your pet and its hearts, the enemy and its health.

In the arena, every command is judged (`judge`): a successful command with the fight's tool hits the
enemy, looking around is free, anything else (or a failed command with the tool) hurts you. At 0
hearts you're knocked out. `start()` runs `python3 launch.py bashou.duel <arena> <shell pid>`, which draws
it at the top right, flashing whoever was hit; the arena's prompt runs `judge` after each command.
"""

import dataclasses
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from . import challenges, creatures, progress, render, state
from .adventure import sprites
from .analyze import analyze, parse_log
from .i18n import _, cap

ESC = "\x1b"
HEARTS = 3
ENEMY = 3                 # health pips; hits bring it to 1, `answer` lands the last blow
KO = 4                    # exit code of the arena shell when you're knocked out
FLASH = 0.6               # seconds a hit flashes
FREE = {"ls", "cd", "pwd", "cat", "head", "tail", "less", "more", "file", "stat", "tree", "echo",
        "clear", "man", "help", "history", "type", "which", "task", "hint", "answer", "flee", "bashou",
        "nano", "vi", "vim", "nvim", "emacs", "micro", "ed", "code"}   # editing a file to fix is fine

ENEMIES = Path(__file__).resolve().parent / "enemies"     # <challenge id>.json, the pet format, facing left
PLACEHOLDER = ((150, 150, 160), (80, 80, 90))              # for a new fight still without its sprite


def judge(ch, status, command):
    """"hit", "hurt" or None (free) for one arena command."""
    found = analyze(command)
    if found.help_only:
        return None                                       # reading the help is never a mistake
    if ch.used_by(found):
        return "hit" if status == 0 else "hurt"
    return None if found.tools <= FREE else "hurt"


def path(base):
    return Path(base) / "duel.json"


def load(base):
    try:
        return json.loads(path(base).read_text())
    except (OSError, ValueError):
        return {"hearts": HEARTS, "enemy": ENEMY, "offset": 0, "event": "", "at": 0, "said": ""}


def cmd_judge(base):
    """After each arena command: score the new ones. Exit code KO when the last heart is gone."""
    base = Path(base)
    ch = challenges.BY_ID[json.loads((base / "meta.json").read_text())["challenge"]]
    d = load(base)
    try:
        data = (base / "log").read_text()
    except FileNotFoundError:
        data = ""
    for status, command in parse_log(data[d["offset"]:]):
        verdict = judge(ch, status, command)
        if verdict == "hit":
            d["enemy"] = max(1, d["enemy"] - 1)
            d["said"] = "💥 " + cap(_("{tool} hits the {threat}!").format(tool=ch.tool, threat=_(ch.threat)))
        elif verdict == "hurt":
            d["hearts"] = max(0, d["hearts"] - 1)
            d["said"] = "✗ " + (_("Missed! ♥ -1") if ch.used_by(analyze(command)) else
                                _("That's not {tool}: ♥ -1").format(tool=ch.tool))
        if verdict:
            d["event"], d["at"] = verdict, time.time()
    d["offset"] = len(data)
    path(base).write_text(json.dumps(d))
    return KO if d["hearts"] <= 0 else 0


def enemy_sprite(ch_id):
    if (ENEMIES / f"{ch_id}.json").exists():
        return creatures.load(ENEMIES / f"{ch_id}.json")
    body, dark = PLACEHOLDER
    rows = sprites.symmetric(sprites.MONSTER)
    rows = rows + ["." * len(rows[0])] * (len(rows) % 2)
    palette = {"a": dark, "o": body, "w": (255, 255, 255), "m": (25, 25, 25)}
    return creatures.Pet(id="enemy", name="", base=rows, palette=palette)


def flashed(pet, rgb):
    return dataclasses.replace(pet, palette={k: rgb for k in pet.palette})


class Scene:
    """Draws the fight panel at the top right, and erases it."""

    def __init__(self, base, shell):
        self.base, self.shell = Path(base), shell
        meta = json.loads((self.base / "meta.json").read_text())
        self.ch = challenges.BY_ID[meta["challenge"]]
        self.task = self.ch.task_text(meta).replace("\n", " ")
        s = state.load()
        sprite, _stage, self.name, _voice = progress.current(s)
        self.look = progress.look(s)
        self.pet = creatures.get(sprite)
        self.enemy = enemy_sprite(self.ch.id)
        self.drawn = ""

    def frame(self, cols, now):
        """(drawing, erase) for this moment."""
        d = load(self.base)
        flash = now - d["at"] < FLASH and int((now - d["at"]) * 10) % 2 == 0
        pet, enemy = self.pet, self.enemy
        if flash and d["event"] == "hit":
            enemy = flashed(enemy, (255, 255, 255))
        if flash and d["event"] == "hurt":
            pet = flashed(pet, (240, 60, 60))
        width = pet.width + 2 + enemy.width
        x = cols - width
        out, rows = [], 1 + max(len(pet.base), len(enemy.base)) // 2
        hearts = "♥" * d["hearts"] + "♡" * (HEARTS - d["hearts"])
        health = "█" * d["enemy"] + "░" * (ENEMY - d["enemy"])
        out.append(f"{ESC}[1;{x}H{ESC}[38;2;240;90;110m{hearts:<{pet.width + 2}}"
                   f"{ESC}[38;2;240;200;90m{health:<{enemy.width}}{ESC}[0m")
        for i, line in enumerate(render.lines(pet, [], [[True] * pet.width] * (len(pet.base) // 2), self.look)):
            out.append(f"{ESC}[{i + 2};{x}H{line}  ")
        for i, line in enumerate(render.lines(enemy, [], [[True] * enemy.width] * (len(enemy.base) // 2))):
            out.append(f"{ESC}[{i + 2};{x + pet.width + 2}H{line}")
        erase = render.erase([[True] * width] * rows, 1, x)
        text = (d["said"] + " · " if d["said"] and now - d["at"] < 6 else "") + self.task
        if x > 24:                                          # the task, in a bubble on the left
            lines, bw = render.bubble(text, min(x - 1, 60), max_lines=rows - 2)
            bx = x - bw
            for i, line in enumerate(lines):
                out.append(f"{ESC}[{i + 1};{bx}H{ESC}[38;2;150;190;230m{line}{ESC}[0m")
            erase += render.erase([[True] * bw] * len(lines), 1, bx)
        return "".join(out), erase

    def height(self):
        return 1 + max(len(self.pet.base), len(self.enemy.base)) // 2

    def fits(self, cols):
        return cols >= self.pet.width + self.enemy.width + 10

    def at_prompt(self):
        try:
            with open(f"/proc/{self.shell}/stat") as f:
                fields = f.read().rsplit(")", 1)[1].split()
        except OSError:
            return False
        return fields[2] == fields[5]

    def run(self):
        erase_file = self.base / "erase"
        last = None
        try:
            while True:
                os.kill(self.shell, 0)                      # OSError when the arena is over
                time.sleep(0.1)
                if not self.at_prompt():
                    last = None                             # PS0 erased us: draw again at the next prompt
                    continue
                cols = os.get_terminal_size(1).columns
                if not self.fits(cols):
                    continue
                body, erase = self.frame(cols, time.time())
                if body == last:
                    continue
                old = self.drawn if self.drawn != erase else ""
                os.write(1, (ESC + "7" + old + body + ESC + "8").encode())
                last, self.drawn = body, erase
                erase_file.write_text(ESC + "7" + erase + ESC + "8")
        finally:
            if self.drawn:                                  # leave the screen clean
                os.write(1, (ESC + "7" + self.drawn + ESC + "8").encode())


def room(base):
    """Terminal lines the panel takes at the top, or 0 when the terminal is too small for it."""
    try:
        cols, lines = os.get_terminal_size(1)
        scene = Scene(base, 0)
    except (OSError, KeyError, ValueError):
        return 0
    return scene.height() if scene.fits(cols) and lines >= scene.height() + 10 else 0


def start(base, shell):
    """The drawing process for the arena shell `shell` (its pid)."""
    root = Path(__file__).resolve().parent.parent
    return subprocess.Popen([sys.executable, str(root / "launch.py"), "bashou.duel", str(base), str(shell)], cwd=root)


def stop(proc):
    if proc:
        proc.terminate()
        try:
            proc.wait(2)
        except subprocess.TimeoutExpired:
            proc.kill()


def main():
    if sys.argv[1:2] == ["judge"]:
        sys.exit(cmd_judge(sys.argv[2]))
    os.setpgrp()                                            # Ctrl-C in the arena isn't for us
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    Scene(sys.argv[1], int(sys.argv[2])).run()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError, OSError):
        pass
