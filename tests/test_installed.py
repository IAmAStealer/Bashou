"""The installed .deb or .rpm, in CI's Debian and Rocky containers (BASHOU_INSTALLED=1, as a normal user).

User report (0.6.2 rpm installed, no `bashou share`): ~/.bashrc still loaded an old git copy. These check
the real package: every command runs from /usr/bin/bashou, and /etc/profile.d/bashou.sh moves a shell
that loads an old copy to the package, in the shells the system reads profile.d from.
"""

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.test_shell import Shell

PACKAGE = Path("/usr/share/bashou")


@unittest.skipUnless(os.environ.get("BASHOU_INSTALLED") == "1", "CI only, once the package is installed")
class InstalledTest(unittest.TestCase):
    def test_every_command_runs(self):
        loader = (PACKAGE / "bashou.bash").read_text()
        commands = [c for c in re.search(r'_bashou_commands="([^"]*)"', loader)[1].split() if c not in ("on", "off")]
        self.assertIn("share", commands)
        with tempfile.TemporaryDirectory() as home:
            for cmd in commands:
                with self.subTest(cmd=cmd):
                    out = subprocess.run(["/usr/bin/bashou", cmd, "--help"], capture_output=True, text=True,
                                         env={"PATH": "/usr/bin:/bin", "HOME": home})
                    self.assertEqual(out.returncode, 0, out.stderr)

    def handover(self, argv):
        """An interactive bash whose ~/.bashrc loads an old copy: the package's loader must take over."""
        with tempfile.TemporaryDirectory() as tmp:
            home, old = Path(tmp) / "home", Path(tmp) / "old"
            home.mkdir()
            old.mkdir()
            (old / "bashou.bash").write_text(f"BASHOU_DIR={old}\nbashou() {{ [[ $1 == off ]] && OLD_OFF=yes; }}\n")
            (home / ".bashrc").write_text(f"[ -f /etc/bashrc ] && . /etc/bashrc\nPS1='$ '\nsource {old}/bashou.bash\n")
            (home / ".bash_profile").write_text(". ~/.bashrc\n")
            sh = Shell(tmp, argv, env={"HOME": str(home), "PYTHONPATH": "", "BASHOU_PACKAGE_LOADER": "",
                                       "BASHOU_KEEP_CLONE": ""})
            try:
                self.assertTrue(sh.expect(b"$ "), sh.out[-500:])
                self.assertEqual(sh.value("BASHOU_DIR"), str(PACKAGE))
                self.assertEqual(sh.value("OLD_OFF"), "yes")
                self.assertTrue(sh.value("BASHOU_PID"))
            finally:
                sh.close()

    def test_login_shell_moves_to_the_package(self):
        self.handover(["bash", "-il"])

    @unittest.skipUnless(Path("/etc/bashrc").exists(), "Fedora and Rocky: every interactive bash reads profile.d")
    def test_terminal_shell_moves_to_the_package(self):
        self.handover(["bash", "-i"])


def zsh_reads_profile_d():
    """Does this system's zsh read /etc/profile (and so profile.d) in a login shell?"""
    for name in ("/etc/zsh/zprofile", "/etc/zprofile"):
        try:
            if "/etc/profile" in Path(name).read_text():
                return True
        except OSError:
            pass
    return False


@unittest.skipUnless(os.environ.get("BASHOU_INSTALLED") == "1", "CI only, once the package is installed")
class InstalledZshTest(unittest.TestCase):
    """0.9.0: a zsh player with the package installed."""

    def zsh(self, argv, zshrc, before=None):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            (home / ".zshrc").write_text(f"PS1='$ '\n{zshrc}")
            env = {"HOME": str(home), "ZDOTDIR": str(home), "PYTHONPATH": "", "BASHOU_PACKAGE_LOADER": "",
                   "BASHOU_KEEP_CLONE": "", "BASHOU_SHELL": ""}
            if before:
                subprocess.run(["zsh", "-c", before], env={**os.environ, **env}, capture_output=True, text=True)
            sh = Shell(tmp, argv, env=env, shell="zsh")
            try:
                self.assertTrue(sh.expect(b"$ "), sh.out[-500:])
                return sh.value("BASHOU_DIR"), sh.value("BASHOU_SHELL"), sh.value("BASHOU_PID")
            finally:
                sh.close()

    @unittest.skipUnless(zsh_reads_profile_d(), "this system's zsh doesn't read profile.d")
    def test_a_login_zsh_loads_the_package(self):
        found, shell, pid = self.zsh(["zsh", "-il"], "")
        self.assertEqual((found, shell), (str(PACKAGE), "zsh"))
        self.assertTrue(pid)

    def test_bashou_on_in_zsh_loads_it_in_new_terminals(self):
        """Where zsh skips profile.d (non-login terminals, Debian), `bashou on` adds the line to ~/.zshrc."""
        found, shell, pid = self.zsh(["zsh", "-i"], "", before="/usr/bin/bashou on")
        self.assertEqual((found, shell), (str(PACKAGE), "zsh"))
        self.assertTrue(pid)


if __name__ == "__main__":
    unittest.main()
