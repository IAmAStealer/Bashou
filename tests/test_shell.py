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
TIMEOUT = 10


class Shell:
    """An interactive bash that sources bashou.bash, with its own data folders."""

    def __init__(self, tmp, cmd=None, state=None):
        self.tmp = Path(tmp)
        self.data, self.cache = self.tmp / "data", self.tmp / "cache"
        self.data.mkdir(exist_ok=True)
        if state is not False:                           # False: first launch, no save yet
            base = {"language": "en", "starter": "star", "active": "starter",
                    "settings": {"updates": "off"}, **(state or {})}
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

    def expect(self, pattern, start=0, timeout=TIMEOUT):
        """Read until `pattern` shows up after byte `start` (True), or the timeout (False).

        Waiting for what we expect, not a fixed time: CI machines are slower than ours.
        """
        end = time.time() + timeout
        while pattern not in self.out[start:] and time.time() < end:
            self.read(0.1)
        return pattern in self.out[start:]

    def value(self, name):
        """Print a shell variable through a marker and read it back."""
        start = len(self.out)
        # "@@V""=" on the command line, "@@V=" only in the printed output.
        os.write(self.fd, f'echo "@@V""=${name}@@"\n'.encode())
        if not self.expect(b"@@V=", start) or not self.expect(b"@@", self.out.index(b"@@V=", start) + 4):
            raise AssertionError(f"no value for {name}")
        rest = self.out[self.out.index(b"@@V=", start) + 4:]
        return rest[:rest.index(b"@@")].decode()

    def state(self):
        return json.loads((self.data / "state.json").read_text())

    def wait_state(self, check, timeout=TIMEOUT):
        """Wait until check(state) is true (the pet saves about once a second)."""
        end = time.time() + timeout
        while time.time() < end:
            try:
                if check(self.state()):
                    return True
            except (OSError, ValueError, KeyError):
                pass
            self.read(0.2)
        return False

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
        self.sh.read(1)
        self.sh.expect(b"38;2;216;200;160")              # the pet is drawn: rc read, pet started

    def test_prompt_starts_below_the_pet(self):
        """The first commands' output hid under the pet (the prompt started on the top line)."""
        self.assertIn(b"\x1b[6B", self.sh.out)             # at startup
        start = len(self.sh.out)
        self.sh.send("clear\n", wait=0.2)
        self.assertTrue(self.sh.expect(b"\x1b[6B", start))  # and after clear
        self.sh.send("echo typed", 0.2)
        start = len(self.sh.out)
        self.sh.send("\x0c", 0)                               # Ctrl+L
        self.assertTrue(self.sh.expect(b"\x1b[2J\x1b[6B", start))
        self.assertTrue(self.sh.expect(b"echo typed", start))   # the line being typed stays

    def tearDown(self):
        pid = ""
        if os.waitpid(self.sh.pid, os.WNOHANG)[0] == 0:  # the shell still runs
            try:
                pid = self.sh.value("BASHOU_PID")
            except (AssertionError, OSError):
                pass
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
        self.sh.send("true 2\n")
        self.assertTrue(self.sh.wait_state(lambda s: s["commands"] == 2))
        self.sh.read(1.5)
        self.assertEqual(self.sh.state()["commands"], 2)       # and not more

    def test_pet_is_erased_before_command_output(self):
        """The pet must be wiped (PS0) before a command prints, or it scrolls into the history."""
        erase = next(self.sh.cache.glob("erase.*")).read_bytes()
        start = len(self.sh.out)
        self.sh.send('echo "OUT_$((40 + 2))"\n', 0)
        self.assertTrue(self.sh.expect(b"OUT_42", start))
        after = self.sh.out[start:]
        self.assertIn(erase, after)
        self.assertLess(after.index(erase), after.index(b"OUT_42"))

    def test_pet_comes_back_right_after_any_command(self):
        """The pet stayed erased up to 2 s, or longer after commands history skips (duplicates)."""
        self.sh.send("true\n", 2)
        start = len(self.sh.out)
        self.sh.send("true\n", 0)                       # duplicate: not logged, no event
        self.assertTrue(self.sh.expect(b"38;2;216;200;160", start, timeout=3))   # stardust color: redrawn

    def test_dead_pet_is_restarted(self):
        """If the pet process dies, the next prompt starts a new one."""
        pet = int(self.sh.value("BASHOU_PID"))
        os.kill(pet, signal.SIGKILL)
        time.sleep(0.2)
        self.sh.send("true\n", 1.5)
        new = int(self.sh.value("BASHOU_PID"))
        end = time.time() + TIMEOUT
        while not alive(new) and time.time() < end:
            time.sleep(0.1)
        self.assertNotEqual(new, pet)
        self.assertTrue(alive(new))

    def test_bubble_stays_across_commands(self):
        """Bubbles vanished after one command; typo jokes were limited to one a minute (`whih` got none)."""
        start = len(self.sh.out)
        self.sh.send("sl\n", 0)
        self.assertTrue(self.sh.expect(b"`ls`", start))
        for _ in range(3):
            start = len(self.sh.out)
            self.sh.send("true\n", 0)
            self.assertTrue(self.sh.expect(b"`ls`", start, timeout=4))   # redrawn after each command
        start = len(self.sh.out)
        self.sh.send("whih\n", 0)
        self.assertTrue(self.sh.expect(b"`which`", start))

    def test_quitting_keeps_bashs_exit_status(self):
        """The terminal said "exited with code 2": bash exits with the last command's status, Bashou
        (its exit trap, its prompt hook) must not change it."""
        for last, code in (("true", 0), ("ls /nope", 2)):
            with tempfile.TemporaryDirectory() as tmp:
                sh = Shell(tmp)
                sh.read(1)
                sh.expect(b"38;2;216;200;160")
                sh.send(last + "\n", 0.5)
                sh.send("\x04", 0)                              # Ctrl+D: logout
                for _ in range(TIMEOUT * 10):
                    done, status = os.waitpid(sh.pid, os.WNOHANG)
                    if done:
                        break
                    time.sleep(0.1)
                os.close(sh.fd)
                self.assertEqual(os.waitstatus_to_exitcode(status), code, last)

    def test_what_you_type_is_private(self):
        """The events file holds every command: 600 in a 700 folder, whatever the umask."""
        events = self.sh.data / f"events.{self.sh.value('$')}"
        self.assertEqual(events.stat().st_mode & 0o777, 0o600)

    def test_exit_cleans_up(self):
        """On exit the pet stops and removes its events/erase files."""
        pet = int(self.sh.value("BASHOU_PID"))
        self.sh.send("exit\n", 0.5)
        for _ in range(TIMEOUT * 10):
            if not alive(pet):
                break
            time.sleep(0.1)
        self.assertFalse(alive(pet))
        self.assertEqual(list(self.sh.cache.glob("erase.*")), [])
        self.assertEqual(list(self.sh.data.glob("events.*")), [])


class FirstLaunchTest(unittest.TestCase):
    def test_first_launch_asks_for_a_starter(self):
        """No save yet: language, skills, then starter, then the pet appears."""
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, state=False)
            try:
                self.assertTrue(sh.expect(b"Language"))
                sh.send("\r", 0)                         # English
                self.assertTrue(sh.expect(b"What do you want to learn?"))
                sh.send("\x1b[B", 0.3)                   # ↓ Pick my skills
                sh.send("\r", 0)
                self.assertTrue(sh.expect(b"Pick your skills"))
                sh.send(" ", 0.3)                        # untick Bash
                sh.send("\r", 0)
                self.assertTrue(sh.expect(b"Choose your starter"))
                sh.send("\x1b[C", 0.3)                   # → Seedling
                sh.send("\r", 0)
                self.assertTrue(sh.wait_state(lambda s: s["starter"] == "sprout"))
                self.assertEqual(sh.state()["language"], "en")
                self.assertNotIn("bash", sh.state()["skills"])
                self.assertIn("python", sh.state()["skills"])
                self.assertTrue(alive(int(sh.value("BASHOU_PID"))))
            finally:
                sh.close()


    def test_old_save_is_asked_the_language_once(self):
        """Saves from before languages keep their starter and only get the language screen."""
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, state={"language": None})
            try:
                self.assertTrue(sh.expect(b"Language"))
                sh.send("\x1b[B", 0.3)                   # ↓ Français
                sh.send("\r", 0)
                self.assertTrue(sh.wait_state(lambda s: s["language"] == "fr"))
                self.assertTrue(sh.expect(b"38;2;216;200;160"))          # straight to the pet
                self.assertNotIn(b"Choose your starter", sh.out)
                self.assertTrue(alive(int(sh.value("BASHOU_PID"))))
            finally:
                sh.close()


class QuitTest(unittest.TestCase):
    def run_and_press(self, key):
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, ["python3", "-m", "bashou", "swap"])
            try:
                self.assertTrue(sh.expect(b"Bashou"))           # the board is up
                sh.send(key, 0)
                end = time.time() + TIMEOUT
                pid = 0
                while not pid and time.time() < end:
                    sh.read(0.1)
                    pid, status = os.waitpid(sh.pid, os.WNOHANG)
                return sh.out, pid
            finally:
                sh.close()

    def test_ctrl_c_on_the_board_is_quiet(self):
        """Ctrl+C on `bashou swap` printed a Python traceback."""
        out, pid = self.run_and_press("\x03")
        self.assertNotIn(b"Traceback", out)
        self.assertNotEqual(pid, 0)                     # it exited

    def test_ctrl_d_closes_the_board(self):
        out, pid = self.run_and_press("\x04")
        self.assertNotIn(b"Traceback", out)
        self.assertNotEqual(pid, 0)


class AdventureShellTest(unittest.TestCase):
    def test_walk_then_save_and_quit(self):
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, ["python3", "-m", "bashou", "adventure"], state={"starter": "pebble"})
            try:
                self.assertTrue(sh.expect(b"The Sleepy Meadow"))
                sh.send("\r", 0.5)                        # set off
                self.assertTrue(sh.expect("▶".encode()))                # the paths are named on the road
                sh.send("\r", 0.5)                        # first path
                sh.send(" ", 1.5)                         # auto-walk
                sh.send("s", 0)
                self.assertTrue(sh.expect(b"Adventure saved"))
                self.assertNotIn(b"Traceback", sh.out)
                self.assertIn(b"\x1b[?1049l", sh.out)    # the normal screen is back
                self.assertGreater(sh.state()["adventure"]["walked"], 2)
            finally:
                sh.close()


    def test_chest_opens_a_shell_and_comes_back(self):
        adv = {"chapter": 1, "leg": 0, "topic": "bash", "segment": 1, "distance": 80.0, "leg_start": 0.0,
               "phase": "chest", "walked": 80.0}
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, ["python3", "-m", "bashou", "adventure"], state={"starter": "pebble", "adventure": adv})
            try:
                self.assertTrue(sh.expect(b"shell trick"))
                sh.send("\r", 0)
                self.assertTrue(sh.expect(b"arena $"))              # a real shell in the sandbox
                sh.send("flee\n", 0)
                self.assertTrue(sh.expect(b"stays shut"))           # back in the game
                sh.send("\r", 0.3)
                sh.send("s", 0)
                self.assertTrue(sh.expect(b"Adventure saved"))
                self.assertNotIn(b"Traceback", sh.out)
                self.assertEqual(sh.state()["adventure"]["segment"], 2)   # the chest is behind us
            finally:
                sh.close()


class SecurityShellTest(unittest.TestCase):
    def test_solve_a_security_challenge(self):
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, ["python3", "-m", "bashou", "security", "2"])
            try:
                self.assertTrue(sh.expect(b"arena $"))           # the sandbox prompt
                self.assertIn(b"Encoded note", sh.out)
                sh.send('answer "$(base64 -d note.txt | cut -d\' \' -f2)"\n', 0)
                self.assertTrue(sh.expect(b"Solved"))
                self.assertTrue(sh.wait_state(lambda s: s["security"] == ["encoded_note"]))
            finally:
                sh.close()


class ArenaShellTest(unittest.TestCase):
    def test_no_fight_without_a_threat(self):
        """`bashou fight` only works once the pet announced a threat."""
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, ["python3", "-m", "bashou", "fight"])
            try:
                self.assertTrue(sh.expect(b"No threat around"))
            finally:
                sh.close()

    def test_ctrl_d_in_the_arena_is_a_flee(self):
        """Ctrl-D after a successful command used to exit with 0 and count as a win."""
        threat = {"threat": {"challenge": "grep_hydra", "until": time.time() + 600}}
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, ["python3", "-m", "bashou", "fight"], state=threat)
            try:
                self.assertTrue(sh.expect(b"arena $"))
                start = len(sh.out)
                sh.send("true\n", 0)
                self.assertTrue(sh.expect(b"arena $", start))
                sh.send("\x04", 0)
                self.assertTrue(sh.expect(b"You fled"))
                self.assertEqual(sh.state()["fights_won"], 0)
            finally:
                sh.close()


if __name__ == "__main__":
    unittest.main()
