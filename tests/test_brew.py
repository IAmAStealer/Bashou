"""Homebrew installs (0.10.0, owner 2026-10-17): the release tarball, the tap's formula, the stable opt/ path
the ~/.zshrc line uses, and `bashou update` pointing at brew."""

import contextlib
import hashlib
import importlib.util
import io
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bashou import brew, repo_setup, setup, update

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("package", ROOT / "tools/package.py")
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)

CELLAR = Path("/opt/homebrew/Cellar/bashou/0.10.0/libexec")
OPT = Path("/opt/homebrew/opt/bashou/libexec")


class StablePathTest(unittest.TestCase):
    def test_cellar_becomes_opt(self):
        """brew upgrade removes the old Cellar folder: a ~/.zshrc line pointing there would load nothing."""
        self.assertEqual(brew.stable(CELLAR / "bashou.zsh"), OPT / "bashou.zsh")
        self.assertEqual(brew.stable(CELLAR), OPT)

    def test_intel_and_linux_prefixes(self):
        self.assertEqual(brew.stable(Path("/usr/local/Cellar/bashou/1.2.3/libexec/bashou.zsh")),
                         Path("/usr/local/opt/bashou/libexec/bashou.zsh"))
        self.assertEqual(brew.stable(Path("/home/linuxbrew/.linuxbrew/Cellar/bashou/1.2.3_1/libexec")),
                         Path("/home/linuxbrew/.linuxbrew/opt/bashou/libexec"))

    def test_other_paths_stay(self):
        for path in (Path.home() / ".bashou/bashou.zsh", Path("/usr/share/bashou/bashou.bash"),
                     Path("/opt/homebrew/Cellar/other/1.0/libexec/bashou.zsh"), Path("/Cellar/bashou")):
            self.assertEqual(brew.stable(path), path)

    def test_installed(self):
        self.assertTrue(brew.installed(CELLAR))
        self.assertTrue(brew.installed(OPT))
        self.assertFalse(brew.installed(Path("/usr/share/bashou")))
        self.assertFalse(brew.installed(ROOT))

    def test_the_zshrc_line_uses_opt(self):
        self.assertEqual(setup.LOADER.parent, brew.stable(ROOT))
        self.assertEqual(setup.line(brew.stable(CELLAR / "bashou.zsh")), f"source {OPT}/bashou.zsh")


class UpgradeTest(unittest.TestCase):
    def test_update_shows_brew_upgrade(self):
        with mock.patch.object(brew, "installed", return_value=True), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(repo_setup.upgrade(run=lambda *a, **k: self.fail("ran without a yes")), 0)
        self.assertIn("brew upgrade bashou", out.getvalue())
        self.assertNotIn("apt", out.getvalue())
        self.assertNotIn("sudo", out.getvalue())


def loader_lines(name, python=False):
    """The lines of `name` (bashou.bash, bashou.zsh) that set BASHOU_DIR (and _bashou_py with `python`)."""
    starts = ("BASHOU_DIR=", "[[ $BASHOU_DIR") + ("_bashou_py=", "[[ -x $BASHOU_DIR/python") * python
    return "\n".join(l for l in (ROOT / name).read_text().splitlines() if l.startswith(starts))


def has(shell):
    return subprocess.run(["sh", "-c", f"command -v {shell}"], capture_output=True).returncode == 0


class LoaderDirTest(unittest.TestCase):
    """The loaders resolve symlinks (opt/bashou -> Cellar/bashou/VERSION): they go back to opt/ themselves,
    so a terminal opened before `brew upgrade` keeps finding Bashou after it."""

    def dir_from(self, shell, loader):
        """BASHOU_DIR as the loader's own lines set it, copied to `loader` and sourced from there."""
        out = subprocess.run([shell, "-c", '_bashou_sticky=$1; source "$1"; printf %s "$BASHOU_DIR"', shell,
                              str(loader)], capture_output=True, text=True, timeout=10)
        self.assertEqual(out.stderr, "")
        return Path(out.stdout)

    def test_cellar_loader_gives_opt(self):
        with tempfile.TemporaryDirectory() as tmp:
            cellar = Path(tmp) / "Cellar/bashou/0.10.0/libexec"
            cellar.mkdir(parents=True)
            (Path(tmp) / "opt").mkdir()
            (Path(tmp) / "opt/bashou").symlink_to(cellar.parent)
            for shell, name in (("bash", "bashou.bash"), ("zsh", "bashou.zsh")):
                if not has(shell):
                    continue
                (cellar / name).write_text(loader_lines(name) + "\n")
                with self.subTest(shell=shell):
                    got = self.dir_from(shell, Path(tmp) / "opt/bashou/libexec" / name)
                    self.assertEqual(got.resolve(), cellar.resolve())
                    self.assertEqual(got.parts[-3:], ("opt", "bashou", "libexec"))

    def test_a_clone_keeps_its_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            for shell, name in (("bash", "bashou.bash"), ("zsh", "bashou.zsh")):
                if not has(shell):
                    continue
                (Path(tmp) / name).write_text(loader_lines(name) + "\n")
                with self.subTest(shell=shell):
                    self.assertEqual(self.dir_from(shell, Path(tmp) / name), Path(tmp).resolve())


class LoaderPythonTest(unittest.TestCase):
    """The loaders run Bashou with the formula's python (libexec/python) when there is one, else python3."""

    def python_from(self, shell, folder):
        lines = loader_lines(shell == "zsh" and "bashou.zsh" or "bashou.bash", python=True)
        (folder / "loader").write_text(lines + "\n")
        out = subprocess.run([shell, "-c", '_bashou_sticky=$1; source "$1"; printf %s "$_bashou_py"', shell, str(folder / "loader")],
                             capture_output=True, text=True, timeout=10)
        self.assertEqual(out.stderr, "")
        return out.stdout

    def test_brew_python_then_python3(self):
        for shell in ("bash", "zsh"):
            if not has(shell):
                continue
            with self.subTest(shell=shell), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                self.assertEqual(self.python_from(shell, folder), "python3")
                (folder / "python").symlink_to("/bin/sh")
                self.assertEqual(self.python_from(shell, folder), str(folder.resolve() / "python"))

    def test_no_bare_python3_left(self):
        for name in ("bashou.bash", "bashou.zsh"):
            with self.subTest(name=name):
                self.assertNotIn('python3 "$BASHOU_DIR', (ROOT / name).read_text())
        from bashou import fight
        self.assertNotIn('python3 "$BASHOU_SRC', Path(fight.__file__).read_text())


class TarballTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dist = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_game_and_its_version_only(self):
        path = package.tarball("1.2.3", self.dist)
        self.assertEqual(path.name, "bashou-1.2.3.tar.gz")
        with tarfile.open(path) as tar:
            names = tar.getnames()
            self.assertEqual(tar.extractfile("bashou-1.2.3/VERSION").read(), b"v1.2.3\n")
            for member in tar.getmembers():
                self.assertEqual((member.uid, member.gid, member.uname), (0, 0, ""))
        self.assertIn("bashou-1.2.3/bashou/__main__.py", names)
        self.assertIn("bashou-1.2.3/bashou.zsh", names)
        self.assertIn("bashou-1.2.3/launch.py", names)
        for name in names:
            self.assertTrue(name == "bashou-1.2.3" or name.startswith("bashou-1.2.3/"), name)
        tops = {name.split("/")[1] for name in names if "/" in name}
        for private in ("tests", "tools", "doc", ".github", "CLAUDE.md", "bug_report"):
            self.assertNotIn(private, tops)

    def test_same_tree_same_bytes(self):
        """The formula's sha256 is checked by brew: building twice must give the same file."""
        first = package.tarball("1.2.3", self.dist / "a").read_bytes()
        second = package.tarball("1.2.3", self.dist / "b").read_bytes()
        self.assertEqual(hashlib.sha256(first).hexdigest(), hashlib.sha256(second).hexdigest())

    def test_build_makes_it_too(self):
        with contextlib.redirect_stdout(io.StringIO()):
            package.build("v1.2.3", self.dist)
        self.assertTrue((self.dist / "bashou-1.2.3.tar.gz").is_file())


class FormulaTest(unittest.TestCase):
    def setUp(self):
        self.text = package.formula("1.2.3", "ab" * 32)

    def test_release_asset_and_checksum(self):
        self.assertIn('url "https://github.com/IAmAStealer/Bashou/releases/download/v1.2.3/bashou-1.2.3.tar.gz"',
                      self.text)
        self.assertIn(f'sha256 "{"ab" * 32}"', self.text)
        self.assertIn('license "MIT"', self.text)
        self.assertIn("class Bashou < Formula", self.text)

    def test_another_url_for_ci(self):
        text = package.formula("0.0.0", "cd" * 32, url="file:///tmp/bashou-0.0.0.tar.gz")
        self.assertIn('url "file:///tmp/bashou-0.0.0.tar.gz"', text)

    def test_installs_in_libexec_with_a_wrapper_on_opt(self):
        self.assertIn('libexec.install Dir["*"]', self.text)
        self.assertIn('#{opt_libexec}/launch.py', self.text)
        self.assertIn("bashou on", self.text)                     # caveats: how to meet the pet
        self.assertIn("bashou version", self.text)                # brew test

    def test_its_own_python(self):
        """Homebrew's python is 3.15 (owner, 2026-10-20): the formula depends on it and runs it by its opt/
        path, so neither the python3 first on PATH nor other installs (Apple's, pyenv, apt) are involved."""
        self.assertIn('depends_on "python@3.15"', self.text)
        self.assertNotIn("uses_from_macos", self.text)
        self.assertIn('libexec.install_symlink Formula["python@3.15"].opt_bin/"python3.15" => "python"', self.text)
        self.assertIn('exec "#{opt_libexec}/python" "#{opt_libexec}/launch.py" bashou "$@"', self.text)
        self.assertNotIn("exec python3", self.text)

    def test_ruby_syntax(self):
        ruby = subprocess.run(["sh", "-c", "command -v ruby"], capture_output=True, text=True).stdout.strip()
        if not ruby:
            self.skipTest("no ruby here")
        with tempfile.NamedTemporaryFile("w", suffix=".rb") as fh:
            fh.write(self.text)
            fh.flush()
            out = subprocess.run([ruby, "-c", fh.name], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_formula_command_reads_the_tarball(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = package.tarball("1.2.3", Path(tmp))
            with contextlib.redirect_stdout(io.StringIO()) as out:
                package.main(["formula", "v1.2.3", str(path)])
            self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), out.getvalue())
        self.assertIn("releases/download/v1.2.3/bashou-1.2.3.tar.gz", out.getvalue())


class VersionTest(unittest.TestCase):
    def test_brew_tree_is_packaged(self):
        """The tarball has VERSION and no .git: `bashou version` and `bashou update` treat it like a .deb."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "VERSION").write_text("v1.2.3\n")
            with mock.patch.object(update, "ROOT", root):
                self.assertEqual(update.packaged(), "v1.2.3")


if __name__ == "__main__":
    unittest.main()
