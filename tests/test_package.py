""".deb/.rpm installs: the staged tree, the VERSION file, `bashou update` and `bashou on` (setup) without git."""

import contextlib
import importlib.util
import io
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from bashou import setup, update

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("package", ROOT / "tools/package.py")
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class StageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tree = package.stage(Path(self.tmp.name) / "tree", "1.2.3")
        self.share = self.tree / package.PREFIX

    def tearDown(self):
        self.tmp.cleanup()

    def test_tree_is_the_game_only(self):
        self.assertTrue((self.share / "bashou/__main__.py").is_file())
        self.assertTrue((self.share / "bashou.bash").is_file())
        self.assertTrue((self.share / "CHANGELOG.md").is_file())      # bashou update shows it in clones
        for private in ("tests", "tools", "doc", ".github", "CLAUDE.md", "bug_report"):
            self.assertFalse((self.share / private).exists(), private)
        self.assertEqual((self.share / "VERSION").read_text(), "v1.2.3\n")

    def test_profile_hands_old_copies_over(self):
        profile = (self.tree / "etc/profile.d/bashou.sh").read_text()
        self.assertIn(f"/{package.PREFIX}/bashou/handover.bash", profile)
        self.assertTrue((self.share / "bashou/handover.bash").is_file())
        for shell in ("sh", "dash"):                                     # login shells that aren't bash skip it
            if shutil.which(shell):
                out = subprocess.run([shell, "-c", profile], capture_output=True, text=True)
                self.assertEqual((out.returncode, out.stderr), (0, ""), shell)
        self.assertIn("/etc/profile.d/bashou.sh", package.SPEC)

    def test_profile_hands_zsh_over_too(self):
        """0.9.0: zsh reads profile.d through its zprofile (`emulate sh`): the package loads there too."""
        profile = (self.tree / "etc/profile.d/bashou.sh").read_text()
        self.assertIn("ZSH_VERSION", profile)
        self.assertIn(f"/{package.PREFIX}/bashou/handover.zsh", profile)
        for name in ("bashou.zsh", "bashou/handover.zsh", "bashou/room.zsh"):
            self.assertTrue((self.share / name).is_file(), name)
        from tests.test_shell import need
        need("zsh")
        out = subprocess.run(["zsh", "-c", f"emulate sh -c '. /dev/stdin'"], input=profile,
                             capture_output=True, text=True)                 # not interactive: nothing
        self.assertEqual((out.returncode, out.stderr), (0, ""))

    @unittest.skipIf(os.geteuid() == 0, "root gets no pet by default")
    def test_an_interactive_zsh_gets_the_pet_from_profile_d(self):
        from tests.test_shell import Shell
        profile = (self.tree / "etc/profile.d/bashou.sh").read_text().replace(f"/{package.PREFIX}", str(ROOT))
        path = Path(self.tmp.name) / "profile.sh"
        path.write_text(profile)
        sh = Shell(self.tmp.name, bashrc=f"emulate sh -c '. {path}'\n", shell="zsh",
                   env={"BASHOU_PACKAGE_DIR": str(ROOT)})
        try:
            self.assertTrue(sh.expect(b"$ "))
            self.assertEqual(sh.value("BASHOU_DIR"), str(ROOT))
            self.assertEqual(sh.value("BASHOU_SHELL"), "zsh")
            self.assertTrue(sh.value("BASHOU_PID"))
        finally:
            sh.close()

    def test_permissions(self):
        self.assertEqual((self.tree / "usr/bin/bashou").stat().st_mode & 0o777, 0o755)
        self.assertEqual((self.share / "bashou/cli.py").stat().st_mode & 0o777, 0o644)

    def test_wrapper_runs_the_staged_code(self):
        wrapper = (self.tree / "usr/bin/bashou").read_text().replace("/" + package.PREFIX, str(self.share))
        out = subprocess.run(["sh", "-c", wrapper, "bashou", "version"], capture_output=True, text=True)
        self.assertIn("v1.2.3", out.stdout)

    def test_every_game_file_is_shipped(self):
        """A user on 0.6.2 reported no `bashou share`: every tracked file of the game must be in the package."""
        tracked = subprocess.run(["git", "ls-files", "bashou", "art", "bashou.bash", "bashou.zsh", "launch.py"],
                                 cwd=ROOT, capture_output=True, text=True).stdout.split()
        if not tracked:
            self.skipTest("not a git clone")
        self.assertTrue("bashou.zsh" in tracked, "bashou.zsh isn't tracked by git")
        missing = [f for f in tracked if not (self.share / f).is_file()]
        self.assertEqual(missing, [])

    def test_wrapper_runs_every_command(self):
        """Each command the shell completes is known to the packaged CLI (--help exits 0)."""
        wrapper = (self.tree / "usr/bin/bashou").read_text().replace("/" + package.PREFIX, str(self.share))
        loader = (self.share / "bashou.bash").read_text()
        commands = [c for c in re.search(r'_bashou_commands="([^"]*)"', loader)[1].split() if c not in ("on", "off")]
        self.assertIn("share", commands)
        for cmd in commands:
            with self.subTest(cmd=cmd):
                out = subprocess.run(["sh", "-c", wrapper, "bashou", cmd, "--help"],
                                     capture_output=True, text=True, env={"PATH": "/usr/bin:/bin",
                                                                         "HOME": self.tmp.name})
                self.assertEqual(out.returncode, 0, out.stderr)

    @unittest.skipUnless(shutil.which("dpkg-deb"), "needs dpkg-deb")
    def test_deb(self):
        deb = package.build_deb(self.tree, "1.2.3", Path(self.tmp.name))
        info = subprocess.run(["dpkg-deb", "-f", str(deb), "Package", "Version", "Depends"],
                              capture_output=True, text=True).stdout
        self.assertIn("Version: 1.2.3", info)
        self.assertIn("python3 (>= 3.9)", info)
        suggests = subprocess.run(["dpkg-deb", "-f", str(deb), "Suggests"], capture_output=True, text=True).stdout
        self.assertIn("zsh", suggests)                               # works with it, doesn't need it
        self.assertNotIn("zsh", info)
        files = subprocess.run(["dpkg-deb", "-c", str(deb)], capture_output=True, text=True).stdout
        self.assertIn("./usr/share/bashou/VERSION", files)
        self.assertIn("root/root", files)


class PackagedInstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = update.ROOT
        update.ROOT = Path(self.tmp.name)
        (update.ROOT / "VERSION").write_text("v1.2.3\n")

    def tearDown(self):
        update.ROOT = self.saved
        self.tmp.cleanup()

    def test_version_comes_from_the_file(self):
        self.assertEqual(update.version(), "v1.2.3")
        self.assertIsNone(update.latest())                       # no daily git fetch either

    def test_update_points_at_the_package_manager(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(update.run(), 0)                  # no terminal here: shown, not run
        self.assertRegex(out.getvalue(), r"apt install --only-upgrade bashou|dnf upgrade --refresh bashou")

    def test_dnf_reads_the_repository_again(self):
        """0.5.0: players were told a new version was out, and `dnf upgrade bashou` said "Nothing to do"
        (dnf keeps a repository's list 48 hours). The command must refresh it, like apt update does."""
        from bashou import repo_setup
        ran = []
        with mock.patch.object(repo_setup, "system", return_value="rocky"), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            repo_setup.upgrade(run=lambda *a, **k: ran.append(a))
        self.assertIn("sudo dnf upgrade --refresh bashou", out.getvalue())
        self.assertIn("expire", package.DNF_REPO)

    def test_a_clone_ignores_a_stray_version_file(self):
        (update.ROOT / ".git").mkdir()
        self.assertIsNone(update.packaged())


class SetupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bashrc = Path(self.tmp.name) / ".bashrc"

    def tearDown(self):
        self.tmp.cleanup()

    def run_setup(self, loader="/usr/share/bashou/bashou.bash"):
        with contextlib.redirect_stdout(io.StringIO()):
            return setup.run(self.bashrc, Path(loader))

    def test_adds_one_line_once(self):
        self.bashrc.write_text("alias ll='ls -l'")                # no newline at the end
        self.run_setup()
        self.run_setup()
        self.assertEqual(self.bashrc.read_text(), "alias ll='ls -l'\nsource /usr/share/bashou/bashou.bash\n")

    def test_a_git_clone_loader_counts(self):
        """`bashou on` outside the shell function sets up: a clone's own line mustn't get a second one."""
        self.bashrc.write_text("source ~/.bashou/bashou.bash\n")
        self.run_setup()
        self.assertEqual(self.bashrc.read_text(), "source ~/.bashou/bashou.bash\n")
        self.bashrc.write_text("# source ~/.bashou/bashou.bash\n")         # commented out: not loaded
        self.run_setup()
        self.assertIn("source /usr/share/bashou/bashou.bash", self.bashrc.read_text())

    def test_on_ends_an_off(self):
        """`bashou on` from a shell without Bashou: the package's loader starts the pet again in new terminals."""
        off = Path(self.tmp.name) / "off"
        off.touch()
        with contextlib.redirect_stdout(io.StringIO()):
            setup.run(self.bashrc, Path("/usr/share/bashou/bashou.bash"), off)
        self.assertFalse(off.exists())

    def test_new_bashrc_and_odd_paths(self):
        self.run_setup("/home/me/my games/bashou.bash")
        self.assertEqual(self.bashrc.read_text(), "source '/home/me/my games/bashou.bash'\n")

    def test_the_rpm_suggests_zsh(self):
        self.assertIn("Suggests: zsh", package.SPEC)


class ZshSetupTest(unittest.TestCase):
    """0.9.0: `bashou on` in zsh writes ~/.zshrc (and the zsh loader), never ~/.bashrc."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_each_shell_has_its_file_and_loader(self):
        with mock.patch.object(Path, "home", return_value=self.home):
            self.assertEqual(setup.target("zsh"), (self.home / ".zshrc", ROOT / "bashou.zsh"))
            self.assertEqual(setup.target("bash"), (self.home / ".bashrc", ROOT / "bashou.bash"))

    def test_a_zsh_loader_counts_as_loaded(self):
        self.assertTrue(setup.loaded("source ~/.bashou/bashou.zsh\n"))
        self.assertFalse(setup.loaded("# source ~/.bashou/bashou.zsh\n"))

    def test_run_for_zsh(self):
        with mock.patch.object(Path, "home", return_value=self.home), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            setup.run(shell="zsh", off=self.home / "off")
        self.assertEqual((self.home / ".zshrc").read_text(), f"source {ROOT / 'bashou.zsh'}\n")
        self.assertFalse((self.home / ".bashrc").exists())
        self.assertIn("source ~/.zshrc", out.getvalue())

    def test_the_current_shell(self):
        with mock.patch.dict(os.environ, {"BASHOU_SHELL": "zsh"}):
            self.assertEqual(setup.current_shell(), "zsh")
        from tests.test_shell import need
        need("zsh")
        code = "from bashou import setup; print(setup.current_shell())"
        env = {k: v for k, v in os.environ.items() if k != "BASHOU_SHELL"}
        env.update(PYTHONPATH=str(ROOT), SHELL="/bin/bash")          # the login shell isn't the one you type in
        for shell in ("zsh", "bash"):
            out = subprocess.run([shell, "-c", f"python3 -c '{code}'; true"], capture_output=True, text=True, env=env)
            self.assertEqual(out.stdout.strip(), shell)

    def test_bashou_on_typed_in_zsh_without_bashou(self):
        """No loader yet: `bashou on` is the Python command, run from zsh. It writes ~/.zshrc."""
        from tests.test_shell import need
        need("zsh")
        env = {k: v for k, v in os.environ.items() if k != "BASHOU_SHELL"}
        env.update(HOME=str(self.home), PYTHONPATH=str(ROOT), BASHOU_DATA=str(self.home / "data"))
        subprocess.run(["zsh", "-c", "python3 -m bashou on; true"], capture_output=True, text=True, env=env)
        self.assertIn("bashou.zsh", (self.home / ".zshrc").read_text())
        self.assertFalse((self.home / ".bashrc").exists())


if __name__ == "__main__":
    unittest.main()
