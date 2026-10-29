"""The Debian and Rocky packaging Bashou shows follows doc/contributing/packages-style.md (owner, 2026-10-26: a quality judge for every kind of
content; 2026-10-29: rules from official sources). Text players read keeps signature checks on and keys in their own file."""

import re
import unittest
from pathlib import Path

from tests.test_bash_style import all_texts

ROOT = Path(__file__).resolve().parent.parent
STYLE = ROOT / "doc" / "contributing" / "packages-style.md"
# Text that teaches a habit the rules forbid. A line showing the mistake on purpose carries ✘, and a line may
# name the old way to say it's gone or never to use it.
BANNED = [
    (re.compile(r"apt-key add"), "P3: a key file in /etc/apt/keyrings/ and Signed-By, not apt-key"),
    (re.compile(r"trusted=yes|--allow-unauthenticated|gpgcheck=0|--nogpgcheck"), "P3/P8: never switch the signature check off"),
    (re.compile(r"curl [^|]*\| *(?:sudo )?(?:ba)?sh\b"), "P4: download, read, then run; never pipe to a shell"),
]
NAMED_AS_WRONG = re.compile(r"\b(?:removed|gone|deprecated|never|no longer|instead of|not|supprimé|jamais|plus|au lieu|pas)\b", re.I)


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
            if re.match(r"\| P\d+ \|", line):
                with self.subTest(rule=line.split("|")[1].strip()):
                    self.assertRegex(line, r"\]\(https://")

    def test_rule_ids_are_unique(self):
        ids = re.findall(r"^\| (P\d+) \|", STYLE.read_text(), re.M)
        self.assertGreater(len(ids), 5)
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
