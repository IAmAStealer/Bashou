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
ARENA_PROMPT = b"arena # " if os.geteuid() == 0 else b"arena $"     # bash's \$: # for root (a container)


class Shell:
    """An interactive bash that sources bashou.bash, with its own data folders."""

    def __init__(self, tmp, cmd=None, state=None, cursor=True, env=None, bashrc=None):
        self.tmp = Path(tmp)
        self.data, self.cache = self.tmp / "data", self.tmp / "cache"
        self.data.mkdir(exist_ok=True)
        if state is not False:                           # False: first launch, no save yet
            base = {"language": "en", "starter": "star", "active": "starter",
                    "settings": {"updates": "off"}, **(state or {})}
            (self.data / "state.json").write_text(json.dumps(base))
        rc = self.tmp / "rc"
        rc.write_text(f"PS1='$ '\nHISTFILE={self.tmp}/hist\nHISTCONTROL=ignoreboth\n"
                      + (bashrc or f"source {ROOT}/bashou.bash\n"))
        env = {**os.environ, "BASHOU_DATA": str(self.data), "BASHOU_CACHE": str(self.cache),
               "PYTHONPATH": str(ROOT), "TERM": "xterm-256color",
               "BASHOU_PACKAGE_LOADER": str(self.tmp / "no-package"), **(env or {})}   # a real one isn't used
        argv = cmd or ["bash", "--rcfile", str(rc), "-i"]
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.execvpe(argv[0], argv, env)
        import fcntl, struct, termios
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 140, 0, 0))
        self.out = b""
        self.row = 12                 # where the cursor is, as this terminal answers ESC[6n
        self.answered = 0             # bytes of output already looked at for ESC[6n
        self.cursor = cursor          # False: a terminal that never answers them

    def answer_cursor_queries(self):
        """Like a real terminal: ESC[6n gets the cursor position (self.row; after ESC[9999;9999H, the
        bottom right corner of the 30x140 screen)."""
        while self.cursor:
            at = self.out.find(b"\x1b[6n", self.answered)
            if at < 0:
                return
            corner = self.out[:at].endswith(b"\x1b[9999;9999H")
            os.write(self.fd, b"\x1b[30;140R" if corner else f"\x1b[{self.row};1R".encode())
            self.answered = at + 4

    def read(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            ready, _, _ = select.select([self.fd], [], [], 0.05)
            if ready:
                try:
                    self.out += os.read(self.fd, 65536)
                except OSError:
                    break
                self.answer_cursor_queries()
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


class PackageHandoverTest(unittest.TestCase):
    """User report (0.6.2 rpm installed, no `bashou share`): ~/.bashrc still loaded an old git copy, which
    dnf never updates. A git copy's loader now hands over to the package, and the package's profile.d
    script moves shells whose ~/.bashrc loads an older copy, at the first prompt."""

    def test_a_clone_loader_sources_the_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "package.bash"
            package.write_text("PACKAGE_LOADED=yes\n")
            sh = Shell(tmp, env={"BASHOU_PACKAGE_LOADER": str(package)})
            try:
                self.assertTrue(sh.expect(b"$ "))
                self.assertEqual(sh.value("PACKAGE_LOADED"), "yes")
                self.assertEqual(sh.value("BASHOU_DIR"), "")            # the clone's loader stopped there
            finally:
                sh.close()

    def test_the_package_moves_a_shell_that_loads_an_old_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / "old"
            old.mkdir()
            (old / "bashou.bash").write_text(f"BASHOU_DIR={old}\nbashou() {{ [[ $1 == off ]] && OLD_OFF=yes; }}\n")
            rc = f"source {ROOT}/bashou/handover.bash\nsource {old}/bashou.bash\n"   # profile.d, then ~/.bashrc
            sh = Shell(tmp, bashrc=rc, env={"BASHOU_PACKAGE_DIR": str(ROOT)})
            try:
                self.assertTrue(sh.expect(b"$ "))
                self.assertEqual(sh.value("BASHOU_DIR"), str(ROOT))
                self.assertEqual(sh.value("OLD_OFF"), "yes")                # the old pet was stopped
                self.assertNotIn("_bashou_handover", sh.value("PROMPT_COMMAND"))
                self.assertTrue(sh.value("BASHOU_PID"))                     # the package's pet runs
            finally:
                sh.close()

    def test_the_package_leaves_its_own_loader_and_kept_clones_alone(self):
        for env in ({"BASHOU_PACKAGE_DIR": str(ROOT)}, {"BASHOU_PACKAGE_DIR": "/elsewhere", "BASHOU_KEEP_CLONE": "1"}):
            with tempfile.TemporaryDirectory() as tmp:
                rc = f"source {ROOT}/bashou/handover.bash\nsource {ROOT}/bashou.bash\nLOADS=1\n"
                sh = Shell(tmp, bashrc=rc, env=env)
                try:
                    self.assertTrue(sh.expect(b"$ "))
                    self.assertEqual(sh.value("BASHOU_DIR"), str(ROOT), env)
                    self.assertNotIn("_bashou_handover", sh.value("PROMPT_COMMAND"))
                finally:
                    sh.close()


class RoomTest(unittest.TestCase):
    """Owner, 2026-09-26: scrolling up, lines of `--help` had holes where the pet and its bubble were
    drawn. The top rows are now emptied before the pet is drawn (their lines go up into the
    scrollback), and the empty rows are deleted when the next command starts."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sh = Shell(self.tmp.name)
        self.assertTrue(self.sh.expect(b"$ "))

    def tearDown(self):
        self.sh.close()
        self.tmp.cleanup()

    def room(self):
        path = self.sh.cache / f"room.{self.sh.pid}"
        return path.read_text().strip() if path.exists() else None

    def test_the_top_rows_go_up_untouched_then_the_empty_rows_go_away(self):
        sh = self.sh
        sh.row = 29                                    # a full screen: the prompt near the bottom
        start = len(sh.out)
        sh.send("echo hi\n", 1)
        # prompt at 29 of 30, 7 rows for the pet, 2 free under the prompt: scroll 8, then 7 blank rows
        self.assertIn(b"\x1b[30;1H" + b"\r\n" * 8 + b"\x1b[H\x1b[7L\x1b[28;1H", sh.out[start:])
        self.assertEqual(self.room(), "1")
        start = len(sh.out)
        sh.row = 29                                    # where Enter left the cursor
        sh.send("true\n", 1)
        self.assertIn(b"\x1b[H\x1b[7M\x1b[22;1H", sh.out[start:])   # PS0: blank rows deleted

    def test_an_empty_enter_deletes_the_last_room_before_making_a_new_one(self):
        """Owner, 2026-09-27: after empty Enters the pet was there three times, one under the other.
        Bash runs no PS0 for an empty line, so the old blank rows (and the pet in them) stayed and
        the next ones were inserted above them."""
        sh = self.sh
        sh.row = 29
        sh.send("echo hi\n", 1)
        start = len(sh.out)
        sh.row = 29                                    # the prompt was at 28: Enter moved it to 29
        sh.send("\n", 1)
        self.assertIn(b"\x1b[H\x1b[7M\x1b[22;1H", sh.out[start:])   # the old room goes first
        self.assertIn(b"\x1b[H\x1b[7L", sh.out[start:])
        self.assertLess(sh.out.index(b"\x1b[7M", start), sh.out.index(b"\x1b[7L", start))

    def test_room_is_made_on_a_clear_screen_without_scrolling(self):
        sh = self.sh
        sh.row = 1
        start = len(sh.out)
        sh.send("clear\n", 1)
        self.assertIn(b"\x1b[30;1H\x1b[H\x1b[7L\x1b[8;1H", sh.out[start:])

    def test_keys_waiting_mean_no_question_and_no_pet(self):
        """Asking the terminal would eat keys typed ahead: then the pet skips this prompt."""
        script = (f"source <(sed -n '/^_bashou_dsr=/,/^_bashou_make_room()/p' {ROOT}/bashou/room.bash | head -n -1)\n"
                  "_bashou_where && echo asked || echo skipped\n")
        import subprocess
        out = subprocess.run(["bash", "-c", script], input="typed ahead\n", capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "skipped")


class ArenaRoomTest(unittest.TestCase):
    """Owner, 2026-09-26: the arena's fight panel still hid lines (drawn over the text, then blanked):
    the arena's prompt now makes the same room as your shell's."""

    def setUp(self):
        from unittest import mock
        from bashou import fight
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name) / "arena-base"
        (self.base / "arena").mkdir(parents=True)
        (self.base / "arena.rc").write_text(fight.RC)
        (self.base / "meta.json").write_text(json.dumps({"challenge": "grep_hydra"}))
        (self.base / "height").write_text("9\n")
        with mock.patch.dict(os.environ, {"BASHOU_ARENA": str(self.base), "BASHOU_SRC": str(ROOT),
                                          "BASHOU_DUEL": "1"}):
            self.sh = Shell(self.tmp.name, ["bash", "--rcfile", str(self.base / "arena.rc"), "-i"])
        self.assertTrue(self.sh.expect(b"arena"))

    def tearDown(self):
        self.sh.close()
        self.tmp.cleanup()

    def test_the_top_rows_go_up_untouched_then_the_empty_rows_go_away(self):
        sh = self.sh
        sh.row = 29
        start = len(sh.out)
        sh.send("echo hi\n", 0)
        # 9 rows for the panel, 2 free under the prompt: scroll 10, then 9 blank rows
        self.assertTrue(sh.expect(b"\x1b[30;1H" + b"\r\n" * 10 + b"\x1b[H\x1b[9L\x1b[28;1H", start))
        self.assertEqual((self.base / "room").read_text().strip(), "1")
        start = len(sh.out)
        sh.row = 29
        sh.send("true\n", 0)
        self.assertTrue(sh.expect(b"\x1b[H\x1b[9M\x1b[20;1H", start))    # PS0: blank rows deleted


class NoCursorReportTest(unittest.TestCase):
    """A terminal that never says where the cursor is: Bashou draws the pet as it always did."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sh = Shell(self.tmp.name, cursor=False)
        self.sh.read(1)
        self.sh.expect(b"38;2;216;200;160", timeout=15)   # after the 2 s wait for an answer

    def tearDown(self):
        self.sh.close()
        self.tmp.cleanup()

    def test_prompt_starts_below_the_pet(self):
        """The first commands' output hid under the pet (the prompt started on the top line)."""
        self.assertIn(b"\x1b[7B", self.sh.out)             # at startup
        start = len(self.sh.out)
        self.sh.send("clear\n", wait=0.2)
        self.assertTrue(self.sh.expect(b"\x1b[7B", start))  # and after clear
        self.sh.send("echo typed", 0.2)
        start = len(self.sh.out)
        self.sh.send("\x0c", 0)                               # Ctrl+L
        self.assertTrue(self.sh.expect(b"\x1b[2J\x1b[7B", start))
        self.assertTrue(self.sh.expect(b"echo typed", start))   # the line being typed stays

    def test_pet_is_erased_before_command_output(self):
        """The pet must be wiped (PS0) before a command prints, or it scrolls into the history."""
        erase = next(self.sh.cache.glob("erase.*")).read_bytes()
        start = len(self.sh.out)
        self.sh.send('echo "OUT_$((40 + 2))"\n', 0)
        self.assertTrue(self.sh.expect(b"OUT_42", start))
        after = self.sh.out[start:]
        self.assertIn(erase, after)
        self.assertLess(after.index(erase), after.index(b"OUT_42"))


class ShellTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sh = Shell(self.tmp.name)
        self.sh.read(1)
        self.sh.expect(b"38;2;216;200;160")              # the pet is drawn: rc read, pet started

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



class OnePetTest(unittest.TestCase):
    """Owner: with several terminals open, each ran its own pet (drawn everywhere, one Python process
    each). Now the first terminal has the pet; the others count their commands for it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.shells = []

    def tearDown(self):
        for sh in self.shells:
            sh.close()
        time.sleep(0.5)
        self.tmp.cleanup()

    def open(self):
        sh = Shell(self.tmp.name)
        self.shells.append(sh)
        sh.read(1)
        return sh

    def test_a_second_terminal_has_no_pet_but_its_commands_count(self):
        first = self.open()
        self.assertTrue(first.expect(b"38;2;216;200;160"))
        second = self.open()
        second.read(1.5)
        self.assertEqual(second.value("BASHOU_PID"), "")
        self.assertNotIn(b"38;2;216;200;160", second.out)
        second.send("true\n")
        second.send("echo hi\n")
        self.assertTrue(first.wait_state(lambda s: s["commands"] == 3))   # value() ran an echo too

    def test_the_pet_moves_when_its_terminal_closes(self):
        first = self.open()
        self.assertTrue(first.expect(b"38;2;216;200;160"))
        pet = int(first.value("BASHOU_PID"))
        second = self.open()
        second.send("true\n")
        first.send("exit\n", 1)
        end = time.time() + TIMEOUT
        while alive(pet) and time.time() < end:
            time.sleep(0.1)
        start = len(second.out)
        second.send("echo moved\n", 0)
        self.assertTrue(second.expect(b"38;2;216;200;160", start))
        self.assertNotEqual(second.value("BASHOU_PID"), "")
        self.assertTrue(second.wait_state(lambda s: s["commands"] >= 2))   # the guest's true is counted

    def test_bashou_off_in_a_guest_keeps_it_without_pet(self):
        first = self.open()
        self.assertTrue(first.expect(b"38;2;216;200;160"))
        second = self.open()
        second.send("bashou off\n")
        first.send("exit\n", 2)
        second.send("true\n", 1)
        self.assertEqual(second.value("BASHOU_PID"), "")


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
                self.assertTrue(sh.expect(ARENA_PROMPT))              # a real shell in the sandbox
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
                self.assertTrue(sh.expect(ARENA_PROMPT))           # the sandbox prompt
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
                self.assertTrue(sh.expect(ARENA_PROMPT))
                start = len(sh.out)
                sh.send("true\n", 0)
                self.assertTrue(sh.expect(ARENA_PROMPT, start))
                sh.send("\x04", 0)
                self.assertTrue(sh.expect(b"You fled"))
                self.assertEqual(sh.state()["fights_won"], 0)
            finally:
                sh.close()


if __name__ == "__main__":
    unittest.main()
