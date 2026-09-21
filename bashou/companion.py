"""Per-terminal background process: animates the pet, counts commands, shows speech bubbles.

Started by bashou.bash as `python3 -m bashou.companion <shell pid>` with stdout on the terminal.
"""

import datetime
import os
import random
import signal
import sys
import time

from . import creatures, dialogue, fight, progress, render, state
from .behavior import Behavior
from .analyze import parse_log

ESC = "\x1b"
TICK = 0.25


def now_ms():
    return int(time.time() * 1000)


class Companion:
    def __init__(self, shell):
        self.shell = shell
        self.events = state.DATA / f"events.{shell}"
        self.erase_file = state.CACHE / f"erase.{shell}"
        self.offset = 0
        self.notes = []            # notifications waiting for the bubble
        self.bubble = None         # (text, until_ms)
        self.drawn = None          # (erase sequence of what is on screen)
        self.last_key = None
        self.tick = 0
        self.busy = True
        self.state_mtime = 0
        self.pet = creatures.get(state.load()["active"])
        self.cells = render.mask(self.pet)
        self.stage = 1
        self.threat = False
        self.behavior = Behavior(now=now_ms())
        self.last_command = now_ms()
        self.talk_at = now_ms() + random.randint(3, 8) * 60_000

    # --- shell ------------------------------------------------------------

    def alive(self):
        try:
            os.kill(self.shell, 0)
            return True
        except OSError:
            return False

    def at_prompt(self):
        """True when the shell itself owns the terminal (no command running)."""
        try:
            with open(f"/proc/{self.shell}/stat") as f:
                fields = f.read().rsplit(")", 1)[1].split()
        except OSError:
            return False
        return fields[2] == fields[5]   # pgrp == tpgid

    # --- events -----------------------------------------------------------

    def read_events(self):
        try:
            with open(self.events, "rb") as f:
                f.seek(self.offset)
                data = f.read()
        except FileNotFoundError:
            return
        end = data.rfind(b"\n") + 1
        if not end:
            return
        self.offset += end
        records = parse_log(data[:end].decode(errors="replace"))
        if not records:
            return
        now = datetime.datetime.now()
        with state.locked() as s:
            for status, command in records:
                self.notes += progress.record(s, status, command, now.date().isoformat(), now.hour)

    def events_size(self):
        try:
            return self.events.stat().st_size
        except FileNotFoundError:
            return 0

    def reload_pet(self):
        try:
            mtime = state.STATE.stat().st_mtime
        except FileNotFoundError:
            return
        if mtime == self.state_mtime:
            return
        self.state_mtime = mtime
        s = state.load()
        pet = creatures.get(s["active"])
        if pet.id != self.pet.id:
            self.pet, self.cells = pet, render.mask(pet)
        self.stage = self.behavior.stage = progress.stage(s, s["active"])
        self.threat = bool(fight.active_threat(s))

    def last_activity(self):
        """Last command, or last key typed: the kernel updates the terminal's atime on input."""
        try:
            typed = int(os.fstat(1).st_atime * 1000)
        except OSError:
            typed = 0
        return max(self.last_command, typed)

    def maybe_talk(self, ms):
        """Every 10-20 minutes at the prompt, the pet says something (if awake and nothing else to say)."""
        if ms < self.talk_at or self.notes or self.bubble or self.behavior.mood == "sleep":
            return
        self.talk_at = ms + random.randint(10, 20) * 60_000
        self.notes.append(dialogue.line(state.load(), self.pet.id))

    def check_threat(self):
        with state.locked() as s:
            note = fight.maybe_threat(s)
        if note:
            self.notes.append(note)
            self.threat = True

    # --- drawing ----------------------------------------------------------

    def frame(self, ms, poses, z, cols):
        """Escape sequence for one frame, and the sequence that erases it."""
        pet = self.pet
        x = cols - pet.width
        out = [f"{ESC}[{i + 1};{x}H{line}" for i, line in enumerate(render.lines(pet, poses, self.cells, self.stage))]
        zr, zc = pet.z_at
        out.append(f"{ESC}[{zr + 1};{x + zc}H{ESC}[38;2;150;190;230m{z:<3}{ESC}[0m")
        erase = render.erase(self.cells, 1, x)

        if self.bubble:
            lines, bw = render.bubble(self.bubble[0], x - 2)
            bx = x - bw
            if bx >= 1:
                for i, line in enumerate(lines):
                    out.append(f"{ESC}[{i + 2};{bx}H{ESC}[38;2;150;190;230m{line}{ESC}[0m")
                erase += render.erase([[True] * bw] * 3, 2, bx)
        return "".join(out), erase

    def draw(self, ms):
        if self.bubble and ms >= self.bubble[1]:
            self.bubble = None
        if not self.bubble and self.notes:
            self.bubble = (self.notes.pop(0), ms + 5000)

        poses, z = self.behavior.frame(ms, self.pet, self.threat, ms - self.last_activity())
        cols = os.get_terminal_size(1).columns
        if cols < self.pet.width + 20:
            return
        key = (tuple(poses), z, cols, self.bubble, self.pet.id, self.stage)
        self.tick += 1
        if key == self.last_key and self.tick % 8:
            return
        self.last_key = key

        body, erase = self.frame(ms, poses, z, cols)
        out = ESC + "7"
        if self.drawn and self.drawn != erase:
            out += self.drawn          # the pet moved or the bubble closed
        out += body + ESC + "8"
        os.write(1, out.encode())
        if erase != self.drawn:
            self.drawn = erase
            self.erase_file.write_text(ESC + "7" + erase + ESC + "8")

    # --- main loop --------------------------------------------------------

    def run(self):
        state.CACHE.mkdir(parents=True, exist_ok=True)
        try:
            while self.alive():
                time.sleep(TICK)
                if not self.at_prompt():
                    self.busy = True
                    continue
                # A new event means a command ran (and PS0 erased us), even one too quick to see.
                size = self.events_size()
                if size != self.offset:
                    self.busy = True
                if self.busy or self.tick % 4 == 0:
                    self.read_events()
                    self.reload_pet()
                if self.tick % 120 == 60:
                    self.check_threat()
                if self.busy:
                    self.busy, self.last_key, self.drawn = False, None, None
                    self.last_command = now_ms()
                self.maybe_talk(now_ms())
                self.draw(now_ms())
        finally:
            for f in (self.events, self.erase_file):
                try:
                    f.unlink()
                except FileNotFoundError:
                    pass


def main():
    # Started from .bashrc before job control is on, so we'd share the shell's process group
    # and die on every Ctrl+C at the prompt. Leave the group, and ignore SIGINT anyway.
    os.setpgrp()
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    Companion(int(sys.argv[1])).run()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError, OSError):
        pass
