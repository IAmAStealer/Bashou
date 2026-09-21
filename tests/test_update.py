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

    def publish(self, message):
        (self.dev / "a").write_text(message)
        git(self.dev, "commit", "-qam", message)
        git(self.dev, "push", "-q", "origin", "HEAD:main")

    def test_new_version_is_announced_then_pulled(self):
        self.assertIsNone(update.check())                 # up to date: nothing to say
        self.publish("Faster pets")
        self.assertIn("bashou update", update.check())
        self.assertEqual(state.load()["update_behind"], 1)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(update.run(), 0)
        self.assertIn("Faster pets", out.getvalue())
        self.assertEqual((update.ROOT / "a").read_text(), "Faster pets")
        self.assertEqual(state.load()["update_behind"], 0)

    def test_once_a_day_and_can_be_turned_off(self):
        self.assertTrue(update.due(now=1_000_000))
        self.assertFalse(update.due(now=1_000_000 + 3600))  # another terminal, same day
        self.assertTrue(update.due(now=1_000_000 + update.DAY))
        with state.locked() as s:
            s["settings"]["updates"] = "off"
        self.assertFalse(update.due(now=1_000_000 + 3 * update.DAY))

    def test_not_a_clone(self):
        update.ROOT = Path(self.tmp.name) / "nowhere"
        self.assertIsNone(update.behind())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(update.run(), 1)


if __name__ == "__main__":
    unittest.main()
