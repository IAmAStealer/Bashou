"""The Python Bashou shows follows doc/contributing/python-style.md (owner, 2026-10-26: "improve quality, like we
did for bash", with official references). Every .py file a fight or chest writes parses with the grammar of
Python 3.9 (Rocky 9's and macOS's python3); the text players read names python3 and never teaches what the rules
forbid."""

import ast
import random
import re
import tempfile
import unittest
from pathlib import Path

from bashou import challenges
from tests.test_bash_style import all_texts

ROOT = Path(__file__).resolve().parent.parent
STYLE = ROOT / "doc" / "contributing" / "python-style.md"
OLDEST = (3, 9)
# The bug a fight's file holds on purpose, since the player fixes it.
ON_PURPOSE = {
    "colon_cobra": SyntaxError,             # the : of a def is missing
}
# Text that teaches a habit the rules forbid. A line showing the mistake on purpose carries ✗ or ✘.
BANNED = [
    (re.compile(r"(?<![\w/.-])python (?=-[cm]\b|\S+\.py\b)"), "Y1: python3, not python"),
    (re.compile(r"\bdef \w+\([^)]*=\s*(\[\]|\{\})"), "Y8: no mutable default"),
]


def fight_files(seeds=range(3)):
    """(fight id, file name, text) of every Python file a fight or chest writes."""
    for c in challenges.ALL + challenges.TRIALS:
        if not c.available():
            continue
        for seed in seeds:
            with tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                try:
                    meta = c.setup(work, random.Random(seed))
                except (OSError, RuntimeError):     # no loopback here (a sandbox): these write no Python
                    continue
                for p in sorted(work.rglob("*.py")):
                    if ".git" not in p.relative_to(work).parts and p.is_file() and not p.is_symlink():
                        yield c.id, p.name, p.read_text()
                if c.cleanup:
                    c.cleanup(meta)


class FightFileTest(unittest.TestCase):
    def test_every_python_file_a_fight_writes_parses_on_3_9(self):
        seen = 0
        for fight, name, text in fight_files():
            seen += 1
            with self.subTest(fight=fight, file=name):
                try:
                    ast.parse(text, name, feature_version=OLDEST)
                except SyntaxError:
                    if ON_PURPOSE.get(fight) is not SyntaxError:
                        raise
        self.assertGreater(seen, 5)

    def test_the_bug_on_purpose_is_still_there(self):
        files = {fight: text for fight, _, text in fight_files(seeds=[0])}
        for fight in ON_PURPOSE:
            if fight in files:
                with self.assertRaises(SyntaxError, msg=fight):
                    ast.parse(files[fight], feature_version=OLDEST)


class TextTest(unittest.TestCase):
    def test_no_text_teaches_what_the_rules_forbid(self):
        for _, lines in all_texts():
            for where, line in lines:
                if "✗" in line or "✘" in line:
                    continue
                for pattern, rule in BANNED:
                    with self.subTest(where=where, rule=rule):
                        self.assertIsNone(pattern.search(line), f"{where}: {line}")


class StyleFileTest(unittest.TestCase):
    def test_every_rule_has_an_online_source(self):
        """Owner (2026-10-26): every rule needs an online reference, official when there is one."""
        for line in STYLE.read_text().splitlines():
            if re.match(r"\| Y[PC]?\d+ \|", line):
                with self.subTest(rule=line.split("|")[1].strip()):
                    self.assertRegex(line, r"\]\(https://")

    def test_rule_ids_are_unique(self):
        ids = re.findall(r"^\| (Y[PC]?\d+) \|", STYLE.read_text(), re.M)
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
