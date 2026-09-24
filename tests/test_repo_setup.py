import io
import contextlib
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest import mock

from bashou import challenges, repo_setup, state


class RepoSetupTest(unittest.TestCase):
    """bashou update moves a git install to apt or dnf, showing every command and asking first (owner)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        home = Path(self.tmp.name)
        self.old = home / ".bashou" / "bashou.bash"
        self.bashrc = home / ".bashrc"
        self.bashrc.write_text("export EDITOR=vim\nsource ~/.bashou/bashou.bash\nalias ll='ls -l'\n")
        for patch in (mock.patch.object(Path, "home", return_value=home),
                      mock.patch.object(state, "DATA", home / "data"), mock.patch.object(state, "STATE", home / "data/state.json")):
            patch.start()
            self.addCleanup(patch.stop)

    def offer(self, family, answer="y", fails=None):
        ran = []
        def run(cmd):
            ran.append(cmd)
            return CompletedProcess(cmd, 1 if fails and fails in cmd else 0)
        out = io.StringIO()
        with mock.patch.object(challenges, "family", return_value=frozenset(family)), \
                mock.patch("builtins.input", return_value=answer), mock.patch("shutil.which", return_value="/usr/bin/curl"), \
                contextlib.redirect_stdout(out):
            code = repo_setup.offer(self.old, self.bashrc, run=run)
        return code, ran, out.getvalue()

    def test_debian_every_command_is_shown_then_run(self):
        code, ran, out = self.offer({"debian", "ubuntu"})
        self.assertEqual(code, 0)
        self.assertEqual([c[:3] for c in ran][-2:], [["sudo", "apt", "update"], ["sudo", "apt", "install"]])
        for cmd in ran:
            self.assertEqual(cmd[0], "sudo")
            self.assertIn(repo_setup.shown(cmd), out)                    # shown before it runs
        self.assertIn("source /usr/share/bashou/bashou.bash", self.bashrc.read_text())
        self.assertNotIn(".bashou/bashou.bash", self.bashrc.read_text())
        self.assertIn("alias ll", self.bashrc.read_text())
        self.assertIn("source ~/.bashou/bashou.bash", (self.bashrc.parent / ".bashrc.bashou-backup").read_text())

    def test_red_hat_uses_dnf(self):
        code, ran, out = self.offer({"rocky", "rhel", "centos", "fedora"})
        self.assertEqual(ran[-1], ["sudo", "dnf", "install", "bashou"])
        self.assertIn("/etc/yum.repos.d/bashou.repo", " ".join(ran[0]))

    def test_no_means_nothing_runs(self):
        code, ran, out = self.offer({"debian"}, answer="")
        self.assertEqual((code, ran), (2, []))
        self.assertIn("source ~/.bashou/bashou.bash", self.bashrc.read_text())

    def test_a_failure_stops_everything(self):
        code, ran, out = self.offer({"debian"}, fails="update")
        self.assertEqual(code, 1)
        self.assertEqual(ran[-1], ["sudo", "apt", "update"])                  # install never ran
        self.assertIn("source ~/.bashou/bashou.bash", self.bashrc.read_text())

    def test_no_promise_about_a_bashrc_that_doesnt_load_this_copy(self):
        self.bashrc.write_text("alias ll='ls -l'\n")
        code, ran, out = self.offer({"debian"}, answer="")
        self.assertNotIn("becomes", out)

    def test_other_systems_keep_git(self):
        code, ran, out = self.offer({"arch"})
        self.assertEqual((code, ran), (1, []))

    def test_the_loader_line_is_found_in_its_usual_forms(self):
        home = str(Path.home())
        for line in ("source ~/.bashou/bashou.bash", ". $HOME/.bashou/bashou.bash", f'source "{home}/.bashou/bashou.bash"',
                     "source ${HOME}/.bashou/bashou.bash  # my pet"):
            self.assertEqual(repo_setup.loader_lines(line, self.old), [0], line)
        for line in ("# source ~/.bashou/bashou.bash", "source ~/other/bashou.bash", "echo ~/.bashou/bashou.bash"):
            self.assertEqual(repo_setup.loader_lines(line, self.old), [], line)

    def test_package_installs_only_show_the_command_without_a_terminal(self):
        run = mock.Mock()
        with mock.patch.object(challenges, "family", return_value=frozenset({"debian"})), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(repo_setup.upgrade(run=run), 0)
        run.assert_not_called()
        self.assertIn("apt install --only-upgrade bashou", out.getvalue())


if __name__ == "__main__":
    unittest.main()


class UpdateOfferTest(unittest.TestCase):
    def test_asked_once_then_git_as_before(self):
        from bashou import update
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(state, "DATA", Path(tmp)), \
                mock.patch.object(state, "STATE", Path(tmp) / "state.json"), \
                mock.patch("sys.stdin.isatty", return_value=True), mock.patch.object(update, "packaged", return_value=None), \
                mock.patch.object(repo_setup, "system", return_value="debian"), \
                mock.patch.object(repo_setup, "offer", return_value=2) as offer, \
                mock.patch.object(update, "available", return_value=None), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(update.run(), 0)
            self.assertTrue(state.load()["packages_declined"])
            update.run()
            self.assertEqual(offer.call_count, 1)                            # "no" is remembered
            update.run(packages=True)
            self.assertEqual(offer.call_count, 2)                            # --packages asks again
