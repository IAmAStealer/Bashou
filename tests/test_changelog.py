import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import changelog  # noqa: E402


class ChangelogTest(unittest.TestCase):
    def test_every_release_has_notes_newest_first(self):
        text = changelog.CHANGELOG.read_text()
        found = changelog.sections(text)
        self.assertIn("v0.2.0", found)
        self.assertTrue(all(found.values()), "a release section is empty")
        versions = [tuple(map(int, v[1:].split("."))) for v in found]
        self.assertEqual(versions, sorted(versions, reverse=True))
        headers = re.findall(r"^## .*$", text, re.M)
        self.assertEqual(len(headers), len(found), "a '## ' header isn't '## v1.2.3 — YYYY-MM-DD'")

    def test_missing_version_refuses(self):
        import contextlib, io
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(changelog.main(["v99.0.0"]), 1)
            self.assertEqual(changelog.main(["v0.2.0"]), 0)


if __name__ == "__main__":
    unittest.main()
