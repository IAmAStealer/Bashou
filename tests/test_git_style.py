"""The git Bashou shows follows doc/contributing/git-style.md (owner, 2026-10-28: a quality judge for every kind of
content). Text players read teaches git switch and git restore (2.23+), not checkout's old forms."""

import re
import unittest
from pathlib import Path

from tests.test_bash_style import all_texts

ROOT = Path(__file__).resolve().parent.parent
STYLE = ROOT / "doc" / "contributing" / "git-style.md"
# Text that teaches a habit the rules forbid. A line showing the mistake on purpose carries ✘.
BANNED = [
    (re.compile(r"git checkout -b\b"), "G1: git switch -c, not checkout -b"),
    (re.compile(r"git checkout -- "), "G1: git restore, not checkout --"),
    (re.compile(r"push -f\b"), "G3: --force-with-lease, and only on your own branch"),
]
# Naming the old form for players with an old git is fine: "(older git: git checkout -b NAME)".
OLD_FORM = re.compile(r"\b(?:older|old|vieux|ancien)\b[^.()]{0,30}git checkout", re.I)


class TextTest(unittest.TestCase):
    def test_no_text_teaches_what_the_rules_forbid(self):
        for _, lines in all_texts():
            for where, line in lines:
                if "✘" in line or OLD_FORM.search(line):
                    continue
                for pattern, rule in BANNED:
                    with self.subTest(where=where, rule=rule):
                        self.assertIsNone(pattern.search(line), f"{where}: {line}")


class StyleFileTest(unittest.TestCase):
    def test_every_rule_has_an_online_source(self):
        """Owner (2026-10-26): every rule needs an online reference, official when there is one."""
        for line in STYLE.read_text().splitlines():
            if re.match(r"\| G\d+ \|", line):
                with self.subTest(rule=line.split("|")[1].strip()):
                    self.assertRegex(line, r"\]\(https://")

    def test_rule_ids_are_unique(self):
        ids = re.findall(r"^\| (G\d+) \|", STYLE.read_text(), re.M)
        self.assertGreater(len(ids), 5)
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
