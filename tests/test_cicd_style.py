"""The CI/CD Bashou shows follows doc/contributing/cicd-style.md (owner, 2026-10-26: a quality judge for every kind of
content; 2026-10-29: rules from official sources). Text players read uses rules: on GitLab and keeps secrets out of the pipeline file."""

import re
import unittest
from pathlib import Path

from tests.test_bash_style import all_texts

ROOT = Path(__file__).resolve().parent.parent
STYLE = ROOT / "doc" / "contributing" / "cicd-style.md"
# Text that teaches a habit the rules forbid. A line showing the mistake on purpose carries ✘, and a line may
# name the old way to say it's gone or never to use it.
BANNED = [
    (re.compile(r"^\s*(?:only|except):"), "CI4: rules:, not only/except"),
    (re.compile(r"pull_request_target"), "CI7: pull_request_target runs fork code with the repository's secrets"),
]
NAMED_AS_WRONG = re.compile(r"\b(?:old|older|deprecated|never|instead of|not|ancien|jamais|au lieu|pas)\b", re.I)


class TextTest(unittest.TestCase):
    def test_no_text_teaches_what_the_rules_forbid(self):
        for _, lines in all_texts():
            for where, line in lines:
                if "✘" in line or NAMED_AS_WRONG.search(line):
                    continue
                for pattern, rule in BANNED:
                    with self.subTest(where=where, rule=rule):
                        self.assertIsNone(pattern.search(line), f"{where}: {line}")



class StyleFileTest(unittest.TestCase):
    def test_every_rule_has_an_online_source(self):
        """Owner (2026-10-26): every rule needs an online reference, official when there is one."""
        for line in STYLE.read_text().splitlines():
            if re.match(r"\| CI\d+ \|", line):
                with self.subTest(rule=line.split("|")[1].strip()):
                    self.assertRegex(line, r"\]\(https://")

    def test_rule_ids_are_unique(self):
        ids = re.findall(r"^\| (CI\d+) \|", STYLE.read_text(), re.M)
        self.assertGreater(len(ids), 5)
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
