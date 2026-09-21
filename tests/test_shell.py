"""End-to-end tests in a real interactive bash on a pseudo-terminal.

These guard the bugs that only show up with job control, a terminal and a live pet.
They take a few seconds each.
"""

import json
import os
import pty
import select
import signal
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Shell:
    """An interactive bash that sources bashou.bash, with its own data folders."""

    def __init__(self, tmp, cmd=None, state=None):
        self.tmp = Path(tmp)
        self.data, self.cache = self.tmp / "data", self.tmp / "cache"
        self.data.mkdir(exist_ok=True)
        if state is not False:                           # False: first launch, no save yet
            base = {"starter": "cat", "active": "starter", **(state or {})}
            (self.data / "state.json").write_text(json.dumps(base))
        rc = self.tmp / "rc"
        rc.write_text(f"PS1='$ '\nHISTFILE={self.tmp}/hist\nHISTCONTROL=ignoreboth\n"
                      f"source {ROOT}/bashou.bash\n")
        env = {**os.environ, "BASHOU_DATA": str(self.data), "BASHOU_CACHE": str(self.cache),
               "PYTHONPATH": str(ROOT), "TERM": "xterm-256color"}
        argv = cmd or ["bash", "--rcfile", str(rc), "-i"]
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.execvpe(argv[0], argv, env)
        import fcntl, struct, termios
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 140, 0, 0))
        self.out = b""

    def read(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            ready, _, _ = select.select([self.fd], [], [], 0.05)
            if ready:
                try:
                    self.out += os.read(self.fd, 65536)
                except OSError:
                    break
        return self.out

    def send(self, text, wait=0.5):
        os.write(self.fd, text.encode())
        self.read(wait)

    def value(self, name):
        """Print a shell variable through a marker and read it back."""
        self.send(f'echo "@@{name}=${name}@@"\n', 0.7)
        marker = f"@@{name}=".encode()
        chunk = self.out[self.out.rindex(marker) + len(marker):]
        return chunk[:chunk.index(b"@@")].decode()

    def state(self):
        return json.loads((self.data / "state.json").read_text())

    def close(self):
        try:
            os.kill(self.pid, signal.SIGKILL)
            os.waitpid(self.pid, 0)
        except OSError:
            pass
        os.close(self.fd)


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


class ShellTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sh = Shell(self.tmp.name)
        self.sh.read(2)                                  # rc, first prompt, pet starts

    def tearDown(self):
        pid = self.sh.value("BASHOU_PID") if alive(self.sh.pid) else ""
        self.sh.close()
        if pid.isdigit() and alive(int(pid)):
            os.kill(int(pid), signal.SIGTERM)
        self.tmp.cleanup()

    def test_ctrl_c_does_not_kill_the_pet(self):
        """The pet was started before job control, in the shell's process group: Ctrl+C killed it."""
        pet = int(self.sh.value("BASHOU_PID"))
        self.assertNotEqual(os.getpgid(pet), os.getpgid(self.sh.pid))
        self.sh.send("\x03", 0.3)
        self.sh.send("\x03", 0.5)
        self.assertTrue(alive(pet))
        self.assertTrue(alive(self.sh.pid))

    def test_empty_enter_is_not_counted(self):
        """Pressing Enter on an empty line must not farm the command counter."""
        self.sh.send("true\n", 0.3)
        for _ in range(5):
            self.sh.send("\n", 0.2)
        self.sh.send("true 2\n", 2.5)                    # the pet reads events about once a second
        self.assertEqual(self.sh.state()["commands"], 2)

    def test_pet_is_erased_before_command_output(self):
        """The pet must be wiped (PS0) before a command prints, or it scrolls into the history."""
        self.sh.read(1.5)
        erase = next(self.sh.cache.glob("erase.*")).read_bytes()
        start = len(self.sh.out)
        self.sh.send('echo "OUT_$((40 + 2))"\n', 1)
        after = self.sh.out[start:]
        self.assertIn(erase, after)
        self.assertLess(after.index(erase), after.index(b"OUT_42"))

    def test_pet_comes_back_right_after_any_command(self):
        """The pet stayed erased up to 2 s, or longer after commands history skips (duplicates)."""
        self.sh.send("true\n", 2)
        start = len(self.sh.out)
        self.sh.send("true\n", 0.6)                     # duplicate: not logged, no event
        self.assertIn(b"38;2;245;167;52", self.sh.out[start:])   # cat fur color: redrawn

    def test_dead_pet_is_restarted(self):
        """If the pet process dies, the next prompt starts a new one."""
        pet = int(self.sh.value("BASHOU_PID"))
        os.kill(pet, signal.SIGKILL)
        time.sleep(0.2)
        self.sh.send("true\n", 1.5)
        new = int(self.sh.value("BASHOU_PID"))
        self.assertNotEqual(new, pet)
        self.assertTrue(alive(new))

    def test_exit_cleans_up(self):
        """On exit the pet stops and removes its events/erase files."""
        pet = int(self.sh.value("BASHOU_PID"))
        self.sh.send("exit\n", 0.5)
        for _ in range(40):
            if not alive(pet):
                break
            time.sleep(0.1)
        self.assertFalse(alive(pet))
        self.assertEqual(list(self.sh.cache.glob("erase.*")), [])
        self.assertEqual(list(self.sh.data.glob("events.*")), [])


class FirstLaunchTest(unittest.TestCase):
    def test_first_launch_asks_for_a_starter(self):
        """No save yet: the picker opens, Enter picks, then the pet appears."""
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, state=False)
            try:
                sh.read(2.5)
                self.assertIn(b"Choose your starter", sh.out)
                sh.send("\x1b[C", 0.3)                   # → Seedling
                sh.send("\r", 2.5)
                self.assertEqual(sh.state()["starter"], "sprout")
                self.assertTrue(alive(int(sh.value("BASHOU_PID"))))
            finally:
                sh.close()


class ArenaShellTest(unittest.TestCase):
    def test_no_fight_without_a_threat(self):
        """`bashou fight` only works once the pet announced a threat."""
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, ["python3", "-m", "bashou", "fight"])
            try:
                sh.read(2)
                self.assertIn(b"No threat around", sh.out)
            finally:
                sh.close()

    def test_ctrl_d_in_the_arena_is_a_flee(self):
        """Ctrl-D after a successful command used to exit with 0 and count as a win."""
        threat = {"threat": {"challenge": "grep_hydra", "until": time.time() + 600}}
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, ["python3", "-m", "bashou", "fight"], state=threat)
            try:
                sh.read(2)
                sh.send("true\n", 0.5)
                sh.send("\x04", 2)
                self.assertIn(b"You fled", sh.out)
                self.assertEqual(sh.state()["fights_won"], 0)
            finally:
                sh.close()


if __name__ == "__main__":
    unittest.main()
