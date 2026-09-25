""".deb/.rpm installs: the staged tree, the VERSION file, `bashou update` and `bashou setup` without git."""

import contextlib
import importlib.util
import io
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

    def test_permissions(self):
        self.assertEqual((self.tree / "usr/bin/bashou").stat().st_mode & 0o777, 0o755)
        self.assertEqual((self.share / "bashou/cli.py").stat().st_mode & 0o777, 0o644)

    def test_wrapper_runs_the_staged_code(self):
        wrapper = (self.tree / "usr/bin/bashou").read_text().replace("/" + package.PREFIX, str(self.share))
        out = subprocess.run(["sh", "-c", wrapper, "bashou", "version"], capture_output=True, text=True)
        self.assertIn("v1.2.3", out.stdout)

    @unittest.skipUnless(shutil.which("dpkg-deb"), "needs dpkg-deb")
    def test_deb(self):
        deb = package.build_deb(self.tree, "1.2.3", Path(self.tmp.name))
        info = subprocess.run(["dpkg-deb", "-f", str(deb), "Package", "Version", "Depends"],
                              capture_output=True, text=True).stdout
        self.assertIn("Version: 1.2.3", info)
        self.assertIn("python3 (>= 3.9)", info)
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
        with mock.patch.object(repo_setup, "system", return_value="redhat"), \
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

    def test_new_bashrc_and_odd_paths(self):
        self.run_setup("/home/me/my games/bashou.bash")
        self.assertEqual(self.bashrc.read_text(), "source '/home/me/my games/bashou.bash'\n")


if __name__ == "__main__":
    unittest.main()
