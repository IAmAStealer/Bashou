"""`bashou update` against a local "GitHub": a bare repo, a clone as the install, a second clone to publish."""

import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path

from bashou import state, update


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                   check=True, capture_output=True)


class UpdateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        self.saved = state.DATA, state.STATE, update.ROOT
        state.DATA, state.STATE = tmp / "data", tmp / "data/state.json"
        git(tmp, "init", "-q", "--bare", "-b", "main", "hub.git")
        git(tmp, "clone", "-q", "hub.git", "dev")
        (tmp / "dev/a").write_text("1")
        git(tmp / "dev", "add", "a")
        git(tmp / "dev", "commit", "-qm", "First")
        git(tmp / "dev", "push", "-q", "origin", "HEAD:main")
        git(tmp, "clone", "-q", "hub.git", "install")
        self.dev, update.ROOT = tmp / "dev", tmp / "install"

    def tearDown(self):
        state.DATA, state.STATE, update.ROOT = self.saved
        self.tmp.cleanup()

    def publish(self, message, tag=None):
        (self.dev / "a").write_text(message)
        git(self.dev, "commit", "-qam", message)
        git(self.dev, "push", "-q", "origin", "HEAD:main")
        if tag:
            git(self.dev, "tag", tag)
            git(self.dev, "push", "-q", "origin", tag)

    def test_update_shows_the_changelog(self):
        (self.dev / "CHANGELOG.md").write_text("# Changelog\n\n## v0.3.0 — 2026-10-01\n\n### Pets\n- Pets can\n  swim\n")
        git(self.dev, "add", "CHANGELOG.md")
        self.publish("Internal refactor", tag="v0.3.0")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(update.run(), 0)
        self.assertIn("Pets:", out.getvalue())
        self.assertIn("• Pets can swim", out.getvalue())                  # one entry per line
        self.assertNotIn("Internal refactor", out.getvalue())

    def test_install_a_given_release_even_an_older_one(self):
        self.publish("Faster pets", tag="v0.2.0")
        self.publish("Swimming pets", tag="v0.3.0")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(update.run(), 0)                     # newest: v0.3.0
            self.assertEqual(update.run("0.2.0"), 0)              # back to v0.2.0 ("v" optional)
            self.assertEqual((update.ROOT / "a").read_text(), "Faster pets")
            self.assertEqual(update.run("v9.9.9"), 1)             # no such release
        self.assertEqual(update.available(), "v0.3.0")            # and the newest is offered again

    def test_version_names_the_release(self):
        self.publish("Faster pets", tag="v0.2.0")
        with contextlib.redirect_stdout(io.StringIO()):
            update.run()
        self.assertEqual(update.version(), "v0.2.0")
        update.ROOT = update.ROOT.parent / "nowhere"                # not a clone
        self.assertIsNone(update.version())

    def test_only_releases_are_offered(self):
        """A commit on main isn't a release: CI hasn't vouched for it."""
        self.publish("Work in progress")
        self.assertIsNone(update.check())
        self.assertEqual(state.load()["update_available"], "")

    def test_new_release_is_announced_then_installed(self):
        self.assertIsNone(update.check())                 # up to date: nothing to say
        self.publish("Faster pets", tag="v0.2.0")
        self.publish("Half done")                          # after the release, not released
        self.assertIn("v0.2.0", update.check())
        self.assertEqual(state.load()["update_available"], "v0.2.0")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(update.run(), 0)
        self.assertIn("Faster pets", out.getvalue())
        self.assertEqual((update.ROOT / "a").read_text(), "Faster pets")
        self.assertEqual(state.load()["update_available"], "")
        self.assertIsNone(update.check())                 # installed now

    def test_newest_version_wins(self):
        self.publish("One", tag="v0.9.0")
        self.publish("Two", tag="v0.10.0")                 # version order, not text order
        self.assertEqual(update.available(), "v0.10.0")

    def test_once_a_day_and_can_be_turned_off(self):
        self.assertTrue(update.due(now=1_000_000))
        self.assertFalse(update.due(now=1_000_000 + 3600))  # another terminal, same day
        self.assertTrue(update.due(now=1_000_000 + update.DAY))
        with state.locked() as s:
            s["settings"]["updates"] = "off"
        self.assertFalse(update.due(now=1_000_000 + 3 * update.DAY))

    def test_not_a_clone(self):
        update.ROOT = Path(self.tmp.name) / "nowhere"
        self.assertIsNone(update.latest())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(update.run(), 1)


if __name__ == "__main__":
    unittest.main()
