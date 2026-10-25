"""End-to-end tests in a real interactive bash, and zsh (0.9.0), on a pseudo-terminal.

These guard the bugs that only show up with job control, a terminal and a live pet.
They take a few seconds each. Each class runs in bash; its Zsh… subclass at the end runs it again in zsh.
"""

import contextlib
import json
import os
import pty
import re
import select
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = 10
ARENA_PROMPT = b"arena # " if os.geteuid() == 0 else b"arena $"     # bash's \$: # for root (a container)


def need(shell):
    """Owner, 0.9.0: the zsh tests are required everywhere, never skipped."""
    if not shutil.which(shell):
        raise AssertionError(f"these tests need {shell}: sudo apt install {shell} (or sudo dnf install {shell})")


class Shell:
    """An interactive bash (or zsh) that sources bashou.bash (bashou.zsh), with its own data folders.
    For zsh, `bashrc` is the text of the .zshrc (in its own ZDOTDIR)."""

    def __init__(self, tmp, cmd=None, state=None, cursor=True, env=None, bashrc=None, shell="bash"):
        need(cmd[0] if cmd and cmd[0] in ("bash", "zsh") else shell)
        self.shell = shell
        self.tmp = Path(tmp)
        self.data, self.cache = self.tmp / "data", self.tmp / "cache"
        self.data.mkdir(exist_ok=True)
        self.home = self.tmp / "home"
        self.home.mkdir(exist_ok=True)
        if state is not False:                           # False: first launch, no save yet
            base = {"language": "en", "starter": "star", "active": "starter",
                    "settings": {"updates": "off"}, **(state or {})}
            (self.data / "state.json").write_text(json.dumps(base))
        rc = self.tmp / "rc"
        zdot = self.tmp / "zdot"
        if shell == "zsh":
            zdot.mkdir(exist_ok=True)
            (zdot / ".zshrc").write_text(f"PS1='$ '\nHISTFILE={self.tmp}/hist\nSAVEHIST=100\nHISTSIZE=100\n"
                                         "setopt HIST_IGNORE_SPACE HIST_IGNORE_DUPS\n"
                                         + (bashrc or f"source {ROOT}/bashou.zsh\n"))
        else:
            rc.write_text(f"PS1='$ '\nHISTFILE={self.tmp}/hist\nHISTCONTROL=ignoreboth\n"
                          + (bashrc or f"source {ROOT}/bashou.bash\n"))
        env = {**os.environ, "BASHOU_DATA": str(self.data), "BASHOU_CACHE": str(self.cache),
               "PYTHONPATH": str(ROOT), "TERM": "xterm-256color",
               "BASHOU_PACKAGE_LOADER": str(self.tmp / "no-package"),            # a real one isn't used
               "HOME": str(self.home),                    # setting up the other shell writes there, not in yours
               # Ubuntu's /etc/zsh/zshrc runs compinit, which stops to ask about the CI runner's group-writable
               # folders ("insecure directories ... [y] or abort compinit [n]?"): every zsh test waited there.
               "skip_global_compinit": "1", **(env or {})}
        if shell == "zsh":
            env.setdefault("ZDOTDIR", str(zdot))
        argv = cmd or (["zsh", "-i"] if shell == "zsh" else ["bash", "--rcfile", str(rc), "-i"])
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
        """Print a shell variable through a marker and read it back. Typed while a program still holds the
        terminal, the line can be lost (restoring the terminal flushes what was typed): it's typed again."""
        start = len(self.out)
        for _ in range(3):
            # "@@V""=" on the command line, "@@V=" only in the printed output.
            os.write(self.fd, f'echo "@@V""=${name}@@"\n'.encode())
            if self.expect(b"@@V=", start, TIMEOUT / 2):
                break
        if not self.expect(b"@@V=", start, 0) or not self.expect(b"@@", self.out.index(b"@@V=", start) + 4):
            raise AssertionError(f"no value for {name}")
        rest = self.out[self.out.index(b"@@V=", start) + 4:]
        return rest[:rest.index(b"@@")].decode()

    def hooks(self):
        """What runs at each prompt: PROMPT_COMMAND in bash, the precmd functions in zsh."""
        return self.value("precmd_functions[*]" if self.shell == "zsh" else "PROMPT_COMMAND")

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
        """Kill the shell. macOS: an exiting process waits until its terminal's output is read, so read on
        until it's gone (CI hung here with a plain waitpid)."""
        try:
            os.kill(self.pid, signal.SIGKILL)
            end = time.time() + TIMEOUT
            while os.waitpid(self.pid, os.WNOHANG) == (0, 0) and time.time() < end:
                self.read(0.05)
        except OSError:
            pass
        try:
            os.close(self.fd)
        except OSError:                                  # already closed by the test
            pass
        self.stop_leftovers()

    def leftovers(self):
        """Processes started by this shell that outlived it (the pet): they carry its BASHOU_CACHE."""
        mark = f"BASHOU_CACHE={self.cache}".encode()
        found = []
        if not os.path.isdir("/proc"):                   # macOS: ps -E prints each process's environment
            out = subprocess.run(["ps", "-Ewwax", "-o", "pid=,command="], capture_output=True).stdout
            for line in out.splitlines():
                pid, _, rest = line.strip().partition(b" ")
                if pid.isdigit() and int(pid) != os.getpid() and mark in rest.split() and alive(int(pid)):
                    found.append(int(pid))
            return found
        for entry in os.listdir("/proc"):
            if entry.isdigit() and entry != str(os.getpid()):
                try:
                    if mark in Path(f"/proc/{entry}/environ").read_bytes().split(b"\0") and alive(int(entry)):
                        found.append(int(entry))
                except OSError:
                    pass
        return found

    def stop_leftovers(self, timeout=3):
        """The release of v0.7.0 failed on a slow CI machine: the pet still wrote in cache/ while the
        test deleted its folder ("Directory not empty"). Stop them and wait until they are gone."""
        seen = set()                  # an exiting process can't be read any more: wait for those found before
        gone = lambda: not self.leftovers() and not any(alive(pid) for pid in seen)
        for sig in (signal.SIGTERM, signal.SIGKILL):
            for pid in self.leftovers():
                seen.add(pid)
                try:
                    os.kill(pid, sig)
                except OSError:
                    pass
            end = time.time() + timeout
            while not gone() and time.time() < end:
                time.sleep(0.05)
            if gone():
                return


def alive(pid):
    """Running: a zombie (finished, not yet reaped by its parent) doesn't count."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    if not os.path.isdir("/proc"):                       # macOS
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout
        return bool(state.strip()) and not state.strip().startswith("Z")
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except (OSError, IndexError):
        return True


class PackageHandoverTest(unittest.TestCase):
    """User report (0.6.2 rpm installed, no `bashou share`): ~/.bashrc still loaded an old git copy, which
    dnf never updates. A git copy's loader now hands over to the package, and the package's profile.d
    script moves shells whose ~/.bashrc loads an older copy, at the first prompt."""
    SHELL = "bash"

    def test_a_clone_loader_sources_the_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / f"package.{self.SHELL}"
            package.write_text("PACKAGE_LOADED=yes\n")
            sh = Shell(tmp, env={"BASHOU_PACKAGE_LOADER": str(package)}, shell=self.SHELL)
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
            ext = self.SHELL
            (old / f"bashou.{ext}").write_text(f"BASHOU_DIR={old}\nbashou() {{ [[ $1 == off ]] && OLD_OFF=yes; }}\n")
            rc = f"source {ROOT}/bashou/handover.{ext}\nsource {old}/bashou.{ext}\n"   # profile.d, then ~/.bashrc
            sh = Shell(tmp, bashrc=rc, env={"BASHOU_PACKAGE_DIR": str(ROOT)}, shell=self.SHELL)
            try:
                self.assertTrue(sh.expect(b"$ "))
                self.assertEqual(sh.value("BASHOU_DIR"), str(ROOT))
                self.assertEqual(sh.value("OLD_OFF"), "yes")                # the old pet was stopped
                self.assertNotIn("_bashou_handover", sh.hooks())
                self.assertTrue(sh.value("BASHOU_PID"))                     # the package's pet runs
            finally:
                sh.close()

    def test_the_package_leaves_its_own_loader_and_kept_clones_alone(self):
        for env in ({"BASHOU_PACKAGE_DIR": str(ROOT)}, {"BASHOU_PACKAGE_DIR": "/elsewhere", "BASHOU_KEEP_CLONE": "1"}):
            with tempfile.TemporaryDirectory() as tmp:
                ext = self.SHELL
                rc = f"source {ROOT}/bashou/handover.{ext}\nsource {ROOT}/bashou.{ext}\nLOADS=1\n"
                sh = Shell(tmp, bashrc=rc, env=env, shell=self.SHELL)
                try:
                    self.assertTrue(sh.expect(b"$ "))
                    self.assertEqual(sh.value("BASHOU_DIR"), str(ROOT), env)
                    self.assertNotIn("_bashou_handover", sh.hooks())
                finally:
                    sh.close()



class PackageOnByDefaultTest(unittest.TestCase):
    """Owner, 2026-10-05: Bashou wasn't on after installing the package; each user had to find `bashou on`.
    The package's profile.d script now starts the pet in every user's bash (not root's), and `bashou off`
    keeps it off in new terminals until `bashou on`."""
    SHELL = "bash"

    def shell(self, tmp, state=None):
        rc = f"source {ROOT}/bashou/handover.{self.SHELL}\n"           # profile.d, and a ~/.bashrc without Bashou
        return Shell(tmp, bashrc=rc, state=state, env={"BASHOU_PACKAGE_DIR": str(ROOT)}, shell=self.SHELL)

    @unittest.skipIf(os.geteuid() == 0, "root gets no pet by default")
    def test_the_pet_starts_without_bashou_on_and_off_holds_for_new_terminals(self):
        with tempfile.TemporaryDirectory() as tmp:
            sh = self.shell(tmp)
            try:
                self.assertTrue(sh.expect(b"$ "))
                self.assertEqual(sh.value("BASHOU_DIR"), str(ROOT))
                self.assertTrue(sh.value("BASHOU_PID"))
                start = len(sh.out)
                sh.send("bashou off\n")
                self.assertTrue(sh.expect(b"in new terminals too", start))
                self.assertTrue((sh.data / "off").exists())
                self.assertEqual(sh.value("BASHOU_PID"), "")
            finally:
                sh.close()
            sh = self.shell(tmp)                                            # a new terminal: no pet
            try:
                self.assertTrue(sh.expect(b"$ "))
                self.assertEqual(sh.value("BASHOU_DIR"), "")
            finally:
                sh.close()
            (sh.data / "off").touch()
            sh = self.shell(tmp)
            try:
                self.assertTrue(sh.expect(b"$ "))
                self.assertTrue(sh.value("BASHOU_DIR") == "")
            finally:
                sh.close()

    @unittest.skipIf(os.geteuid() == 0, "root gets no pet by default")
    def test_bashou_on_clears_the_off_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            sh = self.shell(tmp)
            try:
                self.assertTrue(sh.expect(b"$ "))
                sh.send("bashou off\n")
                self.assertTrue((sh.data / "off").exists())
                sh.send("bashou on\n")
                self.assertFalse((sh.data / "off").exists())
                self.assertTrue(sh.value("BASHOU_PID"))
            finally:
                sh.close()

    @unittest.skipIf(os.geteuid() == 0, "root gets no pet by default")
    def test_closing_the_off_terminal_doesnt_turn_the_pet_back_on_in_a_guest(self):
        """Guests take the pet over when its terminal closes: not after `bashou off`."""
        with tempfile.TemporaryDirectory() as tmp:
            home, guest = self.shell(tmp), None
            try:
                self.assertTrue(home.expect(b"$ "))
                guest = self.shell(tmp)
                self.assertTrue(guest.expect(b"$ "))
                self.assertEqual(guest.value("_bashou_guest"), "1")
                home.send("bashou off\n")
                os.kill(home.pid, signal.SIGKILL)               # not close(): it stops the guest too (same cache)
                os.waitpid(home.pid, 0)
                guest.send("true\n")
                self.assertEqual(guest.value("BASHOU_PID"), "")
            finally:
                home.close()
                if guest:
                    guest.close()

    @unittest.skipIf(os.geteuid() == 0, "root gets no pet by default")
    def test_quitting_the_first_starter_picker_keeps_it_closed_in_new_terminals(self):
        with tempfile.TemporaryDirectory() as tmp:
            sh = self.shell(tmp, state=False)
            try:
                for _ in range(20):                       # language, skills, editor, starter: q through them all
                    if (sh.data / "off").exists():
                        break
                    sh.send("q", 0.5)
                self.assertTrue(sh.expect(b"Bashou stays off"))
                self.assertTrue((sh.data / "off").exists())
            finally:
                sh.close()

    @unittest.skipUnless(os.geteuid() == 0, "only root is left out")
    def test_root_gets_no_pet_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            sh = self.shell(tmp)
            try:
                self.assertTrue(sh.expect(b"$ ") or sh.expect(b"# "))
                self.assertEqual(sh.value("BASHOU_DIR"), "")
            finally:
                sh.close()

class RoomTest(unittest.TestCase):
    """Owner, 2026-09-26: scrolling up, lines of `--help` had holes where the pet and its bubble were
    drawn. The top rows are now emptied before the pet is drawn (their lines go up into the
    scrollback), and the empty rows are deleted when the next command starts."""
    SHELL = "bash"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sh = Shell(self.tmp.name, shell=self.SHELL)
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

    def test_an_empty_enter_keeps_a_room_that_still_fits(self):
        """Owner, 2026-10-23: each Enter made the whole screen flicker. The room was deleted and made
        again (the screen moved up 7 rows and back down) even when nothing had to scroll."""
        sh = self.sh
        sh.row = 12
        sh.send("echo hi\n", 1)
        start = len(sh.out)
        sh.row = 13                                    # Enter moved the prompt one row down, far from the bottom
        sh.send("\n", 1)
        self.assertNotIn(b"\x1b[7M", sh.out[start:])
        self.assertNotIn(b"\x1b[7L", sh.out[start:])
        self.assertEqual(self.room(), "1")

    def test_an_empty_enter_makes_the_room_again_when_the_pet_waits_for_it(self):
        """`bashou on`, or a pet that restarted, writes 0 in the room file: it waits for a new room. An
        empty Enter keeping the old one left the pet undrawn."""
        sh = self.sh
        sh.row = 12
        sh.send("echo hi\n", 1)
        (sh.cache / f"room.{sh.pid}").write_text("0\n")
        start = len(sh.out)
        sh.row = 13
        sh.send("\n", 1)
        self.assertIn(b"\x1b[7L", sh.out[start:])
        self.assertEqual(self.room(), "1")

    def test_a_room_made_again_moves_in_one_frame(self):
        """At the bottom an empty Enter must scroll: the old room goes, the screen scrolls and the new
        room comes in one synchronized frame, asking where the cursor is once, not twice."""
        sh = self.sh
        sh.row = 29
        sh.send("echo hi\n", 1)
        start = len(sh.out)
        sh.row = 29
        sh.send("\n", 1)
        out = sh.out[start:]
        begin, end = out.index(b"\x1b[?2026h"), out.index(b"\x1b[?2026l")
        self.assertLess(begin, out.index(b"\x1b[7M"))
        self.assertLess(out.index(b"\x1b[7L"), end)
        self.assertEqual(out.count(b"\x1b[6n"), 2)    # the cursor, then the screen's corner

    def test_closing_the_shell_stops_its_pet(self):
        """The v0.7.0 release failed: the pet outlived close() and wrote in cache/ during cleanup."""
        pet = int(self.sh.value("BASHOU_PID"))
        self.assertTrue(alive(pet))
        self.sh.close()
        self.assertFalse(alive(pet))
        self.assertEqual(self.sh.leftovers(), [])

    def test_room_is_made_on_a_clear_screen_without_scrolling(self):
        sh = self.sh
        sh.row = 1
        start = len(sh.out)
        sh.send("clear\n", 1)
        self.assertIn(b"\x1b[30;1H\x1b[H\x1b[7L\x1b[8;1H", sh.out[start:])

    def test_keys_waiting_mean_no_question_and_no_pet(self):
        """Asking the terminal would eat keys typed ahead: then the pet skips this prompt."""
        script = (f"source <(sed -n '/^_bashou_dsr=/,/^_bashou_make_room()/p' {ROOT}/bashou/room.{self.SHELL} | sed '$d')\n"
                  "_bashou_where && echo asked || echo skipped\n")
        import subprocess
        out = subprocess.run([self.SHELL, "-c", script], input="typed ahead\n", capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "skipped")

    def test_a_late_answer_is_still_read(self):
        """Owner: ^[[30;120R showed up on the screen. A busy terminal (WSL) answered after the 2 s wait:
        the answer came when nobody read it any more. A terminal that answered once is waited for."""
        script = (f"source <(sed -n '/^_bashou_dsr=/,/^_bashou_make_room()/p' {ROOT}/bashou/room.{self.SHELL} | sed '$d')\n"
                  "_bashou_where; _bashou_where && echo \"@@$_bashou_at@@\" || echo @@skipped@@\n")
        need(self.SHELL)
        pid, fd = pty.fork()
        if pid == 0:
            os.execvp(self.SHELL, [self.SHELL, "-c", script])
        out, asked, end = b"", 0, time.time() + 20
        try:
            while out.count(b"@@") < 2 and time.time() < end:
                if select.select([fd], [], [], 0.05)[0]:
                    try:
                        out += os.read(fd, 4096)
                    except OSError:
                        break
                if out.count(b"\x1b[6n") > asked:         # one question at a time
                    asked += 1
                    if asked == 3:
                        time.sleep(3)                    # the second time, the terminal is busy
                    os.write(fd, b"\x1b[12;5R" if asked % 2 else b"\x1b[30;140R")
        finally:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
            os.close(fd)
        self.assertIn(b"@@12 5 30@@", out)

    def test_the_second_question_waits_for_the_first_answer(self):
        """Owner, 2026-10-23: ^[[30;120R came back on the screen. Both questions went out together; between
        the two reads echo is back on, and the second answer, arriving then, was printed."""
        script = (f"source <(sed -n '/^_bashou_dsr=/,/^_bashou_make_room()/p' {ROOT}/bashou/room.{self.SHELL} | sed '$d')\n"
                  "_bashou_where && echo \"@@$_bashou_at@@\" || echo @@skipped@@\n")
        need(self.SHELL)
        pid, fd = pty.fork()
        if pid == 0:
            os.execvp(self.SHELL, [self.SHELL, "-c", script])
        out, end = b"", time.time() + 20
        try:
            while b"\x1b[6n" not in out and time.time() < end:
                if select.select([fd], [], [], 0.05)[0]:
                    out += os.read(fd, 4096)
            time.sleep(0.5)                              # time for a second question to come out too
            if select.select([fd], [], [], 0.05)[0]:
                out += os.read(fd, 4096)
            self.assertEqual(out.count(b"\x1b[6n"), 1, "asked again before the first answer")
            os.write(fd, b"\x1b[12;5R")
            while out.count(b"\x1b[6n") < 2 and time.time() < end:
                if select.select([fd], [], [], 0.05)[0]:
                    out += os.read(fd, 4096)
            os.write(fd, b"\x1b[30;140R")
            while out.count(b"@@") < 2 and time.time() < end:
                if select.select([fd], [], [], 0.05)[0]:
                    try:
                        out += os.read(fd, 4096)
                    except OSError:
                        break
        finally:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
            os.close(fd)
        self.assertIn(b"@@12 5 30@@", out)

    def test_keys_typed_after_the_first_answer_are_kept(self):
        """CI macOS (v0.10.6): `flee`, typed between the two questions, was read as part of the second
        answer and lost. Keys waiting after the first answer: no second question, the keys stay."""
        for typed, later in ((b"flee\n", b""), (b"fl", b"ee\n")):         # a whole line, or half of one
            with self.subTest(typed=typed):
                self.keys_after_the_first_answer(typed, later)

    def test_ctrl_c_during_the_questions_gives_the_command_its_echo_back(self):
        """bash-judge (v0.10.6): Ctrl+C while waiting for an answer skipped the stty that puts canonical
        mode and echo back: the next commands ran without echo. PS0 (pet and arena) puts them back."""
        if self.SHELL != "bash":
            self.skipTest("zsh puts the terminal back by itself")
        self.assertIn("_bashou_tty_back", (ROOT / "bashou.bash").read_text().split("_bashou_ps0() {")[1].split("}")[0])
        from bashou import fight
        self.assertIn("_bashou_tty_back", fight.RC.split("_arena_ps0() {")[1].split("}")[0])
        script = (f"source <(sed -n '/^_bashou_dsr=/,/^_bashou_make_room()/p' {ROOT}/bashou/room.bash | sed '$d')\n"
                  "_bashou_raw=1; stty -icanon -echo < /dev/tty          # where Ctrl+C left it\n"
                  "_bashou_tty_back\n"
                  "echo \"@@$(stty -a < /dev/tty | tr '\\n' ' ')@@\"\n")
        pid, fd = pty.fork()
        if pid == 0:
            os.execvp("bash", ["bash", "-c", script])
        out, end = b"", time.time() + 20
        try:
            while out.count(b"@@") < 2 and time.time() < end:
                if select.select([fd], [], [], 0.05)[0]:
                    try:
                        out += os.read(fd, 4096)
                    except OSError:
                        break
        finally:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
            os.close(fd)
        flags = out.split(b"@@")[1].split()
        self.assertIn(b"icanon", flags)
        self.assertIn(b"echo", flags)

    def keys_after_the_first_answer(self, typed, later):
        load = "zmodload zsh/zselect\n" if self.SHELL == "zsh" else ""
        script = (f"{load}source <(sed -n '/^_bashou_dsr=/,/^_bashou_make_room()/p' {ROOT}/bashou/room.{self.SHELL} | sed '$d')\n"
                  "_bashou_where && echo \"@@$_bashou_at@@\" || echo @@skipped@@\n"
                  "read -r line; echo \"@@got $line@@\"\n")
        need(self.SHELL)
        pid, fd = pty.fork()
        if pid == 0:
            os.execvp(self.SHELL, [self.SHELL, "-c", script])
        out, end = b"", time.time() + 20
        try:
            while b"\x1b[6n" not in out and time.time() < end:
                if select.select([fd], [], [], 0.05)[0]:
                    out += os.read(fd, 4096)
            os.write(fd, b"\x1b[12;5R" + typed)              # the answer, then keys right behind it
            time.sleep(0.3)
            os.write(fd, later)
            while b"@@got" not in out and time.time() < end:
                if out.count(b"\x1b[6n") > 1:
                    os.write(fd, b"\x1b[30;140R")
                    out = out.replace(b"\x1b[6n", b"", 1)
                if select.select([fd], [], [], 0.05)[0]:
                    try:
                        out += os.read(fd, 4096)
                    except OSError:
                        break
            while b"@@\r\n" not in out[out.find(b"@@got"):] and time.time() < end:
                if select.select([fd], [], [], 0.05)[0]:
                    out += os.read(fd, 4096)
        finally:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
            os.close(fd)
        self.assertIn(b"@@skipped@@", out)
        self.assertIn(b"@@got flee@@", out)


class ArenaRoomTest(unittest.TestCase):
    """Owner, 2026-09-26: the arena's fight panel still hid lines (drawn over the text, then blanked):
    the arena's prompt now makes the same room as your shell's."""
    SHELL = "bash"

    def setUp(self):
        from unittest import mock
        from bashou import fight
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name) / "arena-base"
        (self.base / "arena").mkdir(parents=True)
        (self.base / "meta.json").write_text(json.dumps({"challenge": "grep_hydra"}))
        (self.base / "height").write_text("9\n")
        env = {"BASHOU_ARENA": str(self.base), "BASHOU_SRC": str(ROOT), "BASHOU_DUEL": "1"}
        argv, extra = fight.arena_shell(self.base, self.SHELL)   # writes the arena's rc file for that shell
        with mock.patch.dict(os.environ, {**env, **extra}):
            self.sh = Shell(self.tmp.name, argv, shell=self.SHELL)
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


class HoneyBadgerShellTest(unittest.TestCase):
    """The Honey badger picked a fight (fight.<shell pid> in the cache): the arena opens right after
    the next command, without typing `bashou fight`."""
    SHELL = "bash"

    def test_the_arena_opens_after_the_next_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            threat = {"challenge": "grep_hydra", "until": time.time() + 3600, "badger": True}
            sh = Shell(tmp, state={"pets": ["honey_badger"], "active": "honey_badger", "threat": threat},
                       shell=self.SHELL)
            try:
                sh.read(1)
                sh.send("true\n", 1)
                self.assertNotIn("⚔ arena".encode(), sh.out)              # nothing picked yet: no arena
                (sh.cache / f"fight.{sh.pid}").write_text("1\n")
                start = len(sh.out)
                sh.send("true\n", 0)
                self.assertTrue(sh.expect("⚔ arena".encode(), start))
                self.assertFalse((sh.cache / f"fight.{sh.pid}").exists())  # once
                sh.send("exit\n", 2)                                      # flee
            finally:
                pid = ""
                with contextlib.suppress(AssertionError, OSError):
                    pid = sh.value("BASHOU_PID")
                sh.close()
                if pid.isdigit() and alive(int(pid)):
                    os.kill(int(pid), signal.SIGTERM)


class NoCursorReportTest(unittest.TestCase):
    """A terminal that never says where the cursor is: Bashou draws the pet as it always did."""
    SHELL = "bash"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sh = Shell(self.tmp.name, cursor=False, shell=self.SHELL)
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
    SHELL = "bash"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # Night shift (and its Mouseling) already won: run between midnight and 5 am, its bubbles covered the
        # one a test waited for
        self.sh = Shell(self.tmp.name, state={"achievements": ["night_owl"], "pets": ["bat"]}, shell=self.SHELL)
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
        for last, code in (("true", 0), ("(exit 2)", 2)):
            with tempfile.TemporaryDirectory() as tmp:
                sh = Shell(tmp, shell=self.SHELL)
                sh.read(1)
                sh.expect(b"38;2;216;200;160")
                start = len(sh.out)
                sh.send(last + "\n", 0)
                sh.expect(b"$ ", start)                         # the prompt hook has run
                done = 0
                for i in range(TIMEOUT * 10):
                    if i % 20 == 0:                             # Ctrl+D: logout; again if the hook's terminal
                        sh.send("\x04", 0)                      # question took it (macOS, slower)
                    done, status = os.waitpid(sh.pid, os.WNOHANG)
                    if done:
                        break
                    sh.read(0.1)
                os.close(sh.fd)
                self.assertTrue(done, f"{last}: the shell didn't exit")
                self.assertEqual(os.waitstatus_to_exitcode(status), code, last)

    def test_bashou_on_and_off_always_answer(self):
        """Owner, 2026-10-12: `bashou on` didn't reply. On and off now say what happened, every time."""
        pet = int(self.sh.value("BASHOU_PID"))
        start = len(self.sh.out)
        self.sh.send("bashou on\n", 0)
        self.assertTrue(self.sh.expect(b"is already here", start))
        self.assertEqual(int(self.sh.value("BASHOU_PID")), pet)                 # the same pet
        start = len(self.sh.out)
        self.sh.send("bashou off\n", 0)
        self.assertTrue(self.sh.expect(b"is hidden in this terminal", start))
        self.assertEqual(self.sh.value("BASHOU_PID"), "")
        start = len(self.sh.out)
        self.sh.send("bashou on\n", 0)
        self.assertTrue(self.sh.expect(b"is back", start))
        self.assertTrue(self.sh.value("BASHOU_PID"))

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
    SHELL = "bash"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.shells = []

    def tearDown(self):
        for sh in self.shells:
            sh.close()
        time.sleep(0.5)
        self.tmp.cleanup()

    def open(self):
        # Only the first terminal writes the save: another one would reset what the pet already counted.
        sh = Shell(self.tmp.name, state=False if self.shells else None, shell=self.SHELL)
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

    def test_bashou_here_moves_the_pet_and_counts_each_command_once(self):
        """Owner: move the pet on purpose to the terminal you type in. The new pet must not count the
        guests' commands again (it read their files from the start), and the old terminal becomes a guest."""
        first = self.open()
        self.assertTrue(first.expect(b"38;2;216;200;160"))
        pet = int(first.value("BASHOU_PID"))                               # 1 command
        second = self.open()
        second.send("true\n")                                              # 2
        self.assertTrue(first.wait_state(lambda s: s["commands"] == 2))
        start = len(second.out)
        second.send("bashou here\n", 0)                                    # 3
        self.assertTrue(second.expect(b"moved to this terminal", start))
        self.assertTrue(second.expect(b"38;2;216;200;160", start))
        end = time.time() + TIMEOUT
        while alive(pet) and time.time() < end:
            first.read(0.1)                    # a full terminal would block the old pet's drawing
        self.assertFalse(alive(pet))                                       # the old pet left by itself
        first.send("true\n")                                               # 4, as a guest
        self.assertEqual(first.value("BASHOU_PID"), "")                    # 5
        self.assertTrue(second.wait_state(lambda s: s["commands"] == 5))
        second.read(2)
        self.assertEqual(second.state()["commands"], 5)                    # and not more
        self.assertFalse((second.data / f"guest.{second.pid}").exists())   # its guest file was read and removed
        start = len(second.out)
        second.send("bashou here\n", 0)
        self.assertTrue(second.expect(b"already lives in this terminal", start))

    def test_ctrl_l_in_a_guest_leaves_no_empty_rows(self):
        """Owner: Ctrl+L in a second terminal put the prompt 7 rows down, under a pet that isn't there."""
        first = self.open()
        self.assertTrue(first.expect(b"38;2;216;200;160"))
        second = self.open()
        start = len(second.out)
        second.send("\x0c", 1)
        self.assertTrue(second.expect(b"\x1b[H\x1b[2J", start))
        after = second.out[second.out.index(b"\x1b[H\x1b[2J", start) + 7:]
        self.assertNotRegex(after, rb"\x1b\[\d+B")
        self.assertIn(b"$ ", after)

    def test_bashou_on_in_a_guest_points_to_bashou_here(self):
        """The pet lives in the first terminal: `bashou on` in another one says where, and doesn't take it."""
        first = self.open()
        self.assertTrue(first.expect(b"38;2;216;200;160"))
        pet = int(first.value("BASHOU_PID"))
        second = self.open()
        start = len(second.out)
        second.send("bashou on\n", 0)
        self.assertTrue(second.expect(b"lives in another terminal", start))
        self.assertEqual(second.value("BASHOU_PID"), "")
        self.assertTrue(alive(pet))

    def test_bashou_off_in_a_guest_keeps_it_without_pet(self):
        first = self.open()
        self.assertTrue(first.expect(b"38;2;216;200;160"))
        second = self.open()
        second.send("bashou off\n")
        first.send("exit\n", 2)
        second.send("true\n", 1)
        self.assertEqual(second.value("BASHOU_PID"), "")


class FirstLaunchTest(unittest.TestCase):
    SHELL = "bash"

    def test_first_launch_asks_for_a_starter(self):
        """No save yet: language, skills, editor, then starter, then the pet appears."""
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, state=False, shell=self.SHELL)
            try:
                self.assertTrue(sh.expect(b"Language"))
                sh.send("\r", 0)                         # English
                self.assertTrue(sh.expect(b"What do you want to learn?"))
                sh.send("\x1b[B", 0.3)                   # ↓ Pick my skills
                sh.send("\r", 0)
                self.assertTrue(sh.expect(b"Pick your skills"))
                sh.send(" ", 0.3)                        # untick Bash
                sh.send("\r", 0)
                self.assertTrue(sh.expect(b"Which editor do you want to learn?"))
                sh.send("\x1b[B", 0.3)                   # ↓ vi
                sh.send("\r", 0)
                self.assertTrue(sh.expect(b"Choose your starter"))
                sh.send("\x1b[C", 0.3)                   # → Seedling
                sh.send("\r", 0)
                self.assertTrue(sh.wait_state(lambda s: s["starter"] == "sprout"))
                self.assertEqual(sh.state()["language"], "en")
                self.assertEqual(sh.state()["settings"]["editor"], "vi")
                self.assertNotIn("bash", sh.state()["skills"])
                self.assertIn("python", sh.state()["skills"])
                self.assertTrue(alive(int(sh.value("BASHOU_PID"))))
            finally:
                sh.close()


    def test_old_save_is_asked_the_language_once(self):
        """Saves from before languages keep their starter and only get the language screen."""
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, state={"language": None}, shell=self.SHELL)
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
    SHELL = "bash"

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
            sh = Shell(tmp, ["python3", "-m", "bashou", "adventure"], state={"starter": "pebble", "adventure": adv},
                       env={"BASHOU_SHELL": self.SHELL}, shell=self.SHELL)
            try:
                self.assertTrue(sh.expect(b"shell trick"))
                sh.send("\r", 0)
                self.assertTrue(sh.expect(ARENA_PROMPT))              # a real shell in the sandbox
                self.assertEqual(sh.value("BASHOU_ARENA_SHELL"), self.SHELL)   # the player's shell
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
    SHELL = "bash"

    def test_solve_a_security_challenge(self):
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, ["python3", "-m", "bashou", "security", "2"], env={"BASHOU_SHELL": self.SHELL},
                       shell=self.SHELL)
            try:
                self.assertTrue(sh.expect(ARENA_PROMPT))           # the sandbox prompt
                self.assertIn(b"Encoded note", sh.out)
                self.assertNotIn(b"real bash", sh.out)             # zsh players get a zsh sandbox
                self.assertEqual(sh.value("BASHOU_ARENA_SHELL"), self.SHELL)
                sh.send('answer "$(base64 -d < note.txt | cut -d\' \' -f2)"\n', 0)
                self.assertTrue(sh.expect(b"Solved"))
                self.assertTrue(sh.wait_state(lambda s: s["security"] == ["encoded_note"]))
            finally:
                sh.close()


class ArenaShellTest(unittest.TestCase):
    SHELL = "bash"

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
            sh = Shell(tmp, ["python3", "-m", "bashou", "fight"], state=threat, env={"BASHOU_SHELL": self.SHELL},
                       shell=self.SHELL)
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

    def test_the_arena_is_the_players_shell_and_its_commands_count(self):
        """0.9.0: a zsh player fights in zsh. The arena's commands are logged like the shell's and count."""
        threat = {"threat": {"challenge": "grep_hydra", "until": time.time() + 600}}
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, ["python3", "-m", "bashou", "fight"], state={**threat, "commands": 0},
                       env={"BASHOU_SHELL": self.SHELL}, shell=self.SHELL)
            try:
                self.assertTrue(sh.expect(ARENA_PROMPT))
                start = len(sh.out)
                version = sh.value("ZSH_VERSION" if self.SHELL == "zsh" else "BASH_VERSION")
                self.assertRegex(version, r"^\d")
                # Typed before the next prompt, a line can be lost (zsh drops typeahead): wait for it.
                self.assertTrue(sh.expect(ARENA_PROMPT, sh.out.index(b"@@V=", start)))
                start = len(sh.out)
                other = sh.value("BASH_VERSION" if self.SHELL == "zsh" else "ZSH_VERSION")
                self.assertEqual(other, "")
                # Each line waits for the prompt, as a player would (CI rocky lost one typed before it)
                self.assertTrue(sh.expect(ARENA_PROMPT, sh.out.index(b"@@V=", start)))
                start = len(sh.out)
                sh.send("task\n", 0)
                self.assertTrue(sh.expect(b"app.log", start))              # the arena's own commands work
                self.assertTrue(sh.expect(ARENA_PROMPT, sh.out.index(b"app.log", start)))
                start = len(sh.out)
                sh.send("printf '%s\\n' one \\\n two\n", 0)              # a command on two lines
                self.assertTrue(sh.expect(b"one\r\ntwo\r\n", start))
                # Wait for the prompt, as a player would: typed while the room is made, `flee` was lost
                self.assertTrue(sh.expect(ARENA_PROMPT, sh.out.index(b"one\r\ntwo\r\n", start)))
                sh.send("flee\n", 0)
                self.assertTrue(sh.expect(b"You fled"))
                self.assertTrue(sh.wait_state(lambda s: s["commands"] >= 4),     # CI macOS failed here (v0.10.6)
                                f"commands={sh.state().get('commands')}\n{sh.out[-3000:].decode(errors='replace')}")
            finally:
                sh.close()


class LoaderTest(unittest.TestCase):
    """What both loaders (bashou.bash, bashou.zsh) must do the same way, for the pet and the Python side."""
    SHELL = "bash"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sh = Shell(self.tmp.name, shell=self.SHELL)
        self.assertTrue(self.sh.expect(b"38;2;216;200;160"))

    def tearDown(self):
        self.sh.close()
        self.tmp.cleanup()

    def events(self):
        from bashou.analyze import parse_log
        return parse_log((self.sh.data / f"events.{self.sh.pid}").read_text())

    def test_the_loader_says_which_shell_it_runs_in(self):
        """The arena, `bashou on` and the lessons for zsh players ask BASHOU_SHELL."""
        self.assertEqual(self.sh.value("BASHOU_SHELL"), self.SHELL)

    def test_each_command_is_logged_whole_with_its_status(self):
        self.sh.send("(exit 2)\n", 0.5)          # GNU ls /nope says 2, macOS's says 1
        self.sh.send("for i in 1 2; do\n  echo $i\ndone\n", 0.5)
        self.sh.send("true\n", 0.5)
        end = time.time() + TIMEOUT
        while len(self.events()) < 3 and time.time() < end:
            self.sh.read(0.2)
        events = self.events()
        self.assertIn((2, "(exit 2)"), events)
        loop = [(s, c) for s, c in events if c.startswith("for i")]      # bash joins its lines with "; "
        self.assertEqual(len(loop), 1, events)
        self.assertEqual(loop[0][0], 0)
        self.assertRegex(loop[0][1], r"^for i in 1 2; do[\s;]+echo \$i[\s;]+done$")
        self.assertEqual(events[-1], (0, "true"))


class OtherShellTest(unittest.TestCase):
    """Owner, 2026-10-12: installed in bash, zsh had no pet. Bash adds Bashou to ~/.zshrc at its next start
    (zsh adds it to ~/.bashrc), once, and says so."""

    def test_the_first_start_sets_up_the_other_shell(self):
        for shell, other, line in (("bash", ".zshrc", "bashou.zsh"), ("zsh", ".bashrc", "bashou.bash")):
            with self.subTest(shell), tempfile.TemporaryDirectory() as tmp:
                sh = Shell(tmp, shell=shell)
                try:
                    self.assertTrue(sh.expect(other.encode()))
                    self.assertIn(line, (sh.home / other).read_text())
                finally:
                    sh.close()
                sh = Shell(tmp, shell=shell)                     # once: not again, even once removed
                try:
                    (sh.home / other).write_text("# mine\n")
                    self.assertTrue(sh.expect(b"38;2;216;200;160"))
                    sh.read(1)
                    self.assertEqual((sh.home / other).read_text(), "# mine\n")
                finally:
                    sh.close()


class ZshCompletionTest(unittest.TestCase):
    """`bashou <Tab>` in zsh, where the player's .zshrc turned completion on (compinit)."""

    def test_tab_completes_bashou_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = f"autoload -Uz compinit && compinit -u\nsource {ROOT}/bashou.zsh\n"
            sh = Shell(tmp, bashrc=rc, shell="zsh")
            try:
                self.assertTrue(sh.expect(b"38;2;216;200;160"))
                self.assertEqual(sh.value("_comps[bashou]"), "_bashou")
                start = len(sh.out)
                sh.send("bashou swa\t", 1)
                end = time.time() + TIMEOUT                    # zle redraws with cursor moves between letters
                plain = lambda: re.sub(rb"\x1b\[[0-9;?]*[A-Za-z]|\x1b[78]", b"", sh.out[start:])
                while b"bashou swap " not in plain() and time.time() < end:
                    sh.read(0.2)
                self.assertIn(b"bashou swap ", plain())
            finally:
                sh.close()

    def test_tab_completes_without_compinit_too(self):
        """Owner, 2026-10-12: Tab did nothing in a bare ~/.zshrc (zsh's first-run one: no compinit)."""
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, shell="zsh")
            try:
                self.assertTrue(sh.expect(b"38;2;216;200;160"))
                for typed, want in (("bashou swa\t", b"bashou swap "), ("fr\t", b"bashou swap frog "),
                                    ("\x15bashou config la\t", b"bashou config language ")):
                    start = len(sh.out)
                    sh.send(typed, 1)
                    plain = lambda: re.sub(rb"\x1b\[[0-9;?]*[A-Za-z]|\x1b[78=>]|\x08", b"", sh.out[start:])
                    end = time.time() + TIMEOUT
                    while want.split(b" ")[-2] not in plain() and time.time() < end:
                        sh.read(0.2)
                    self.assertTrue(want.split(b" ")[-2] + b" " in plain(), typed)
            finally:
                sh.close()

    def test_no_compinit_no_error(self):
        """Without compinit (a bare .zshrc), Bashou loads without a compdef error."""
        with tempfile.TemporaryDirectory() as tmp:
            sh = Shell(tmp, shell="zsh")
            try:
                self.assertTrue(sh.expect(b"38;2;216;200;160"))
                self.assertNotIn(b"command not found", sh.out)
                self.assertNotIn(b"compdef", sh.out)
            finally:
                sh.close()


# --- the same tests in zsh (0.9.0) ------------------------------------------------------------------

class ZshPackageHandoverTest(PackageHandoverTest):
    SHELL = "zsh"


class ZshPackageOnByDefaultTest(PackageOnByDefaultTest):
    SHELL = "zsh"


class ZshRoomTest(RoomTest):
    SHELL = "zsh"


class ZshArenaRoomTest(ArenaRoomTest):
    SHELL = "zsh"


class ZshHoneyBadgerShellTest(HoneyBadgerShellTest):
    SHELL = "zsh"


class ZshNoCursorReportTest(NoCursorReportTest):
    SHELL = "zsh"


class ZshShellTest(ShellTest):
    SHELL = "zsh"


class ZshOnePetTest(OnePetTest):
    SHELL = "zsh"


class ZshFirstLaunchTest(FirstLaunchTest):
    SHELL = "zsh"


class ZshAdventureShellTest(AdventureShellTest):
    SHELL = "zsh"


class ZshSecurityShellTest(SecurityShellTest):
    SHELL = "zsh"


class ZshArenaShellTest(ArenaShellTest):
    SHELL = "zsh"


class ZshLoaderTest(LoaderTest):
    SHELL = "zsh"


if __name__ == "__main__":
    unittest.main()
