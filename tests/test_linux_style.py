"""The Linux system content Bashou shows follows doc/contributing/linux-style.md (owner, 2026-10-29: a dedicated judge
for Linux and systemd). Text players read never opens a file to everyone, puts a service's secret in Environment=,
or lets root log in by SSH."""

import re
import unittest
from pathlib import Path

from tests.test_bash_style import all_texts

ROOT = Path(__file__).resolve().parent.parent
STYLE = ROOT / "doc" / "contributing" / "linux-style.md"
# Text that teaches a habit the rules forbid. A line showing the mistake on purpose carries ✘, and a line may
# name the bad habit to say never to use it.
BANNED = [
    (re.compile(r"chmod (?:-R )?0?777"), "LX2: open a file only as far as needed, never 777"),
    (re.compile(r"Environment=\S*(?:PASSWORD|SECRET|TOKEN)", re.I), "LX8: LoadCredential= or a root-only EnvironmentFile="),
    (re.compile(r"PermitRootLogin yes"), "LX13: PermitRootLogin no or prohibit-password"),
]
NAMED_AS_WRONG = re.compile(r"\b(?:never|not|don't|instead|jamais|pas|plutôt)\b", re.I)


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
            if re.match(r"\| LX\d+ \|", line):
                with self.subTest(rule=line.split("|")[1].strip()):
                    self.assertRegex(line, r"\]\(https://")

    def test_rule_ids_are_unique(self):
        ids = re.findall(r"^\| (LX\d+) \|", STYLE.read_text(), re.M)
        self.assertGreater(len(ids), 5)
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
