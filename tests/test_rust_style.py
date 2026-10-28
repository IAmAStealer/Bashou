"""The Rust Bashou shows follows doc/contributing/rust-style.md (owner, 2026-10-28: a quality judge for every kind
of content). The player builds a fight's file with the command its task shows (rustc file.rs, rustc's default
edition) while verify builds it with --edition 2021: both must see the same errors."""

import random
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from bashou import challenges

ROOT = Path(__file__).resolve().parent.parent
STYLE = ROOT / "doc" / "contributing" / "rust-style.md"


def fight_files():
    """(fight id, work folder, file name) of every Rust file a fight writes, in a folder that lives until the
    caller is done."""
    for c in challenges.ALL + challenges.TRIALS:
        if c.skill != "rust" or not c.available():
            continue
        tmp = tempfile.TemporaryDirectory()
        work = Path(tmp.name)
        meta = c.setup(work, random.Random(0))
        for p in sorted(work.rglob("*.rs")):
            yield c.id, work, p.name
        if c.cleanup:
            c.cleanup(meta)
        tmp.cleanup()


def errors(work, name, *edition):
    done = subprocess.run(["rustc", *edition, name, "-o", "prog"], cwd=work, capture_output=True, text=True,
                          timeout=120)
    return sorted(set(re.findall(r"^error.*$", done.stderr, re.M)))


@unittest.skipUnless(shutil.which("rustc"), "no rustc")
class FightFileTest(unittest.TestCase):
    def test_the_players_command_and_verify_see_the_same_errors(self):
        seen = 0
        for fight, work, name in fight_files():
            seen += 1
            with self.subTest(fight=fight, file=name):
                self.assertEqual(errors(work, name), errors(work, name, "--edition", "2021"))
        self.assertGreater(seen, 5)


class StyleFileTest(unittest.TestCase):
    def test_every_rule_has_an_online_source(self):
        """Owner (2026-10-26): every rule needs an online reference, official when there is one."""
        for line in STYLE.read_text().splitlines():
            if re.match(r"\| R[C]?\d+ \|", line):
                with self.subTest(rule=line.split("|")[1].strip()):
                    self.assertRegex(line, r"\]\(https://")

    def test_rule_ids_are_unique(self):
        ids = re.findall(r"^\| (R[C]?\d+) \|", STYLE.read_text(), re.M)
        self.assertGreater(len(ids), 5)
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
