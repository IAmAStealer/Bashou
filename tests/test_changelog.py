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

    def test_every_new_release_hides_the_breaking_change_pony(self):
        """Owner, 2026-10-09: from v0.8.4 on, each release ends with a joke "Breaking change" line that leads
        to a hidden pony (bashou/pony.py). The joke changes every time; the word stays.
        Owner, 2026-10-10: those sections have "### Changes" then "### Breaking changes", the pony line in the latter."""
        from bashou import pony
        for version, notes in changelog.sections(changelog.CHANGELOG.read_text()).items():
            if tuple(map(int, version[1:].split("."))) > (0, 8, 3):
                titles = re.findall(r"^### (.+)$", notes, re.M)
                self.assertEqual(titles, ["Changes", "Breaking changes"], version)
                breaking = notes.split("### Breaking changes", 1)[1]
                found = re.search(r"Breaking change.*`bashou pony (\w+)`", breaking)
                self.assertTrue(found, f"{version}: no \"Breaking change\" line with `bashou pony <word>`")
                self.assertEqual(pony.PONIES.get(pony.digest(found.group(1))), "pony_wrecking", version)

    def test_missing_version_refuses(self):
        import contextlib, io
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(changelog.main(["v99.0.0"]), 1)
            self.assertEqual(changelog.main(["v0.2.0"]), 0)


if __name__ == "__main__":
    unittest.main()
