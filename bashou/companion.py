"""Per-terminal background process: animates the pet, counts commands, shows speech bubbles.

Started by bashou.bash as `python3 -m bashou.companion <shell pid>` with stdout on the terminal.
"""

import datetime
import os
import random
import signal
import sys
import threading
import time
from pathlib import Path

from . import creatures, dialogue, fight, i18n, progress, render, state, update
from .behavior import Behavior
from .analyze import parse_log

ESC = "\x1b"
TICK = 0.25
SOURCE = Path(__file__).resolve().parent


def code_version():
    """Newest mtime of our source files: it changes on `git pull` or an edit."""
    return max(p.stat().st_mtime for p in SOURCE.rglob("*.py"))


def now_ms():
    return int(time.time() * 1000)


class Companion:
    def __init__(self, shell, offset=0):
        self.shell = shell
        self.events = state.DATA / f"events.{shell}"
        self.erase_file = state.CACHE / f"erase.{shell}"
        self.offset = offset       # bytes of the events file already counted
        self.code = code_version()
        self.notes = []            # notifications waiting for the bubble
        self.bubble = None         # (text, commands run since shown, commands it stays)
        self.drawn = None          # (erase sequence of what is on screen)
        self.last_key = None
        self.tick = 0
        self.busy = True
        self.state_mtime = 0
        sprite, _, _, self.voice = progress.current(state.load())
        self.pet = creatures.get(sprite)
        self.cells = render.mask(self.pet)
        self.stage = 1
        self.threat = False
        self.behavior = Behavior(now=now_ms())
        self.last_command = now_ms()
        self.talk_at = now_ms() + random.randint(3, 8) * 60_000
        self.typo_at = 0
        self.warn_at = 0

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
                if self.bubble:
                    self.bubble = (self.bubble[0], self.bubble[1] + 1, self.bubble[2])
                self.notes += progress.record(s, status, command, now.date().isoformat(), now.hour)
                if status == 127:
                    self.laugh_at_typo(s, command)
                self.warn_remote_script(command)

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
        i18n.use(None)                 # `bashou language` may have changed it
        s = state.load()
        sprite, stage, _, self.voice = progress.current(s)
        if sprite != self.pet.id:
            self.pet = creatures.get(sprite)
            self.cells = render.mask(self.pet)
        self.stage = self.behavior.stage = stage
        self.threat = bool(fight.active_threat(s))

    def last_activity(self):
        """Last command, or last key typed: the kernel updates the terminal's atime on input."""
        try:
            typed = int(os.fstat(1).st_atime * 1000)
        except OSError:
            typed = 0
        return max(self.last_command, typed)

    def laugh_at_typo(self, s, command):
        """`command not found`: a kind joke, at most once a minute."""
        ms = now_ms()
        if ms < self.typo_at:
            return
        line = dialogue.typo(s, self.voice, command)
        if line:
            self.typo_at = ms + 60_000
            self.notes.insert(0, line)

    def warn_remote_script(self, command):
        """`curl … | sh`: a safety warning, shown right away (at most once every 5 minutes)."""
        ms = now_ms()
        if ms < self.warn_at:
            return
        line = dialogue.remote_script(self.voice, command)
        if line:
            self.warn_at = ms + 5 * 60_000
            self.notes.insert(0, line)
            self.bubble = None

    def maybe_talk(self, ms):
        """Every 10-20 minutes at the prompt, the pet says something (if awake and nothing else to say)."""
        if ms < self.talk_at or self.notes or self.bubble or self.behavior.mood == "sleep":
            return
        self.talk_at = ms + random.randint(10, 20) * 60_000
        self.notes.append(dialogue.line(state.load(), self.voice))

    def check_update(self):
        """Once a day, in the background (git may take a while): a bubble if a new version is out."""
        try:
            if update.due():
                note = update.check()
                if note:
                    self.notes.append(note)
        except Exception:
            log_error()

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
                erase += render.erase([[True] * bw] * len(lines), 2, bx)
        return "".join(out), erase

    def update_bubble(self):
        """A bubble stays for a few commands (`bashou config bubble`), 2 at most when another note waits."""
        if self.bubble:
            text, shown, stays = self.bubble
            if shown >= (min(stays, 2) if self.notes else stays):
                self.bubble = None
        if not self.bubble and self.notes:
            self.bubble = (self.notes.pop(0), 0, random.randint(*state.setting(state.load(), "bubble")))

    def draw(self, ms):
        self.update_bubble()

        poses, z = self.behavior.frame(ms, self.pet, self.threat, ms - self.last_activity())
        cols = os.get_terminal_size(1).columns
        if cols < self.pet.width + 20:
            return
        key = (tuple(poses), z, cols, self.bubble and self.bubble[0], self.pet.id, self.stage)
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

    def step(self):
        if not self.at_prompt():
            self.busy = True
            return
        # A new event (or the prompt's SIGUSR1) means a command ran and PS0 erased us.
        if self.events_size() != self.offset:
            self.busy = True
        if self.busy or self.tick % 4 == 0:
            self.read_events()
            self.reload_pet()
        if self.tick % 120 == 60:
            self.check_threat()
        if self.tick == 80:              # 20 s after the start, not to slow down the first prompt
            threading.Thread(target=self.check_update, daemon=True).start()
        if self.busy:
            self.busy, self.last_key, self.drawn = False, None, None
            self.last_command = now_ms()
        if self.tick % 20 == 10 and self.code_changed():
            self.read_events()
            self.restart()
        self.maybe_talk(now_ms())
        self.draw(now_ms())

    def code_changed(self):
        """True once the source changed and has been quiet for 2 s (not in the middle of a save)."""
        try:
            newest = code_version()
        except (OSError, ValueError):
            return False
        return newest != self.code and time.time() - newest > 2

    def restart(self):
        """Run the new code in this same process (same PID, so the shell still knows us)."""
        if self.drawn:
            os.write(1, (ESC + "7" + self.drawn + ESC + "8").encode())
        # A handler doesn't survive exec, an ignored signal does: no SIGUSR1 death in between.
        signal.signal(signal.SIGUSR1, signal.SIG_IGN)
        os.execv(sys.executable, [sys.executable, "-m", "bashou.companion", str(self.shell), str(self.offset)])

    def run(self):
        state.CACHE.mkdir(parents=True, exist_ok=True)
        errors = 0
        try:
            while self.alive():
                time.sleep(TICK)
                self.tick += 1
                try:
                    self.step()
                    errors = 0
                except Exception:
                    # Never let one bad frame kill the pet: log it and keep going.
                    errors += 1
                    log_error()
                    if errors >= 20:
                        raise
        finally:
            for f in (self.events, self.erase_file):
                try:
                    f.unlink()
                except FileNotFoundError:
                    pass

def log_error():
    """Append the traceback to ~/.cache/bashou/errors.log (kept small)."""
    import traceback
    log = state.CACHE / "errors.log"
    try:
        old = log.read_text()[-20000:] if log.exists() else ""
        log.write_text(old + f"--- {datetime.datetime.now():%F %T}\n{traceback.format_exc()}")
    except OSError:
        pass


def main():
    # Started from .bashrc before job control is on, so we'd share the shell's process group
    # and die on every Ctrl+C at the prompt. Leave the group, and ignore SIGINT anyway.
    os.setpgrp()
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    companion = Companion(int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 0)
    # The prompt sends SIGUSR1 after every command: redraw right away.
    signal.signal(signal.SIGUSR1, lambda *_: setattr(companion, "busy", True))
    companion.run()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError, OSError):
        pass
