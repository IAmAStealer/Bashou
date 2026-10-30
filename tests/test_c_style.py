"""The C Bashou shows follows doc/contributing/c-style.md (owner, 2026-10-28: a quality judge for every kind of
content). Every .c file a fight writes is standard C99 with no warning under -Wall -Wextra -pedantic (macOS
builds it with clang, Rocky 9 with gcc 11), except the bug a fight asks to fix."""

import random
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from bashou import challenges

ROOT = Path(__file__).resolve().parent.parent
STYLE = ROOT / "doc" / "contributing" / "c-style.md"
STRICT = ["-std=c99", "-pedantic", "-Wall", "-Wextra", "-fsyntax-only"]
# The bug a fight's file holds on purpose, since the player fixes it: what gcc says about it, and clang (gcc on a
# Mac) in its own words.
ON_PURPOSE = {
    "semicolon_slug": re.compile(r"expected [‘']?;"),
    "warning_wraith": re.compile(r"-Wparentheses"),
}
# Bugs on purpose only clang notices: allowed, not required, since gcc says nothing.
CLANG_SEES = {
    "stack_specter": re.compile(r"-Winfinite-recursion"),
}


def diagnostics(c):
    """(file name, gcc's errors and warnings) of every C file this fight writes."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        meta = c.setup(work, random.Random(0))
        for p in sorted(work.rglob("*.c")):
            done = subprocess.run(["gcc", *STRICT, p.name], cwd=p.parent, capture_output=True, text=True,
                                  timeout=60)
            yield p.name, re.findall(r"^\S+:\d+:\d+: (?:error|warning): .*$", done.stderr, re.M)
        if c.cleanup:
            c.cleanup(meta)


@unittest.skipUnless(shutil.which("gcc"), "no gcc")
class FightFileTest(unittest.TestCase):
    def test_every_c_file_a_fight_writes_is_strict_c99(self):
        seen = 0
        for c in challenges.ALL + challenges.TRIALS:
            if c.skill != "c" and "gcc" not in (c.requires or []):
                continue
            for name, found in diagnostics(c):     # syntax only needs gcc, not gdb
                seen += 1
                with self.subTest(fight=c.id, file=name):
                    allowed = [r for r in (ON_PURPOSE.get(c.id), CLANG_SEES.get(c.id)) if r]
                    self.assertTrue(all(any(r.search(line) for r in allowed) for line in found), found)
        self.assertGreater(seen, 5)

    def test_the_bug_on_purpose_is_still_there(self):
        fights = {c.id: c for c in challenges.ALL + challenges.TRIALS}
        for fight, expected in ON_PURPOSE.items():
            with self.subTest(fight=fight):
                found = [line for _, lines in diagnostics(fights[fight]) for line in lines]
                self.assertTrue(any(expected.search(line) for line in found), found)


class ClangWordsTest(unittest.TestCase):
    def test_the_bugs_on_purpose_are_known_in_clangs_words_too(self):
        """CI for 0.12.0 failed on macOS, where gcc is clang: these are its lines for the two fights."""
        self.assertRegex("hello.c:14:28: error: expected ';' after expression", ON_PURPOSE["semicolon_slug"])
        self.assertRegex("sum.c:14:1: warning: all paths through this function will call itself [-Winfinite-recursion]",
                         CLANG_SEES["stack_specter"])


class StyleFileTest(unittest.TestCase):
    def test_every_rule_has_an_online_source(self):
        """Owner (2026-10-26): every rule needs an online reference, official when there is one."""
        for line in STYLE.read_text().splitlines():
            if re.match(r"\| C[D]?\d+ \|", line):
                with self.subTest(rule=line.split("|")[1].strip()):
                    self.assertRegex(line, r"\]\(https://")

    def test_rule_ids_are_unique(self):
        ids = re.findall(r"^\| (C[D]?\d+) \|", STYLE.read_text(), re.M)
        self.assertGreater(len(ids), 5)
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
