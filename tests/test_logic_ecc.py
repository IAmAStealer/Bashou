"""Codes that fix themselves (owner, 2026-10-31, en.wikipedia.org/wiki/Error_correction_code): a parity bit
finds a flipped bit, Hamming(7,4) finds which one and flips it back. The fights hand a bash decoder with one
check bent; verify sends it every word with every one-bit flip."""

import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from bashou import challenges
from bashou.challenges import logic
from tests.test_fight import SOLUTIONS
from tests.test_logic_scale import arena


def bash(cmd, work):
    return subprocess.run(["bash", "-c", cmd], cwd=work, capture_output=True, text=True, timeout=60).stdout


class HammingTest(unittest.TestCase):
    def test_the_code_fixes_every_single_flip(self):
        """The words verify sends: 16 messages, each sent clean and with each of its 7 bits flipped."""
        cases = logic.hamming_cases()
        self.assertEqual(len(cases), 16 * 8)
        for word, data in cases:
            self.assertRegex(word, r"^[01]{7}$")
            self.assertRegex(data, r"^[01]{4}$")
        self.assertEqual(logic.hamming("1011"), "0110011")      # p1 p2 d1 p4 d2 d3 d4

    def test_printf_formats_stay_on_one_line(self):
        """A \\n in the Python source used to land as a real newline inside the scripts' printf formats."""
        for fight, names in (("bitflip_banshee", ("fix_bits.sh", "test_fix_bits.sh")),
                             ("trial_logic_parity", ("parity.sh", "test_parity.sh"))):
            tmp, work, ch, meta = arena(fight)
            with tmp:
                for name in names:
                    for line in (work / name).read_text().splitlines():
                        if "printf '" in line:
                            self.assertEqual(line.count("'") % 2, 0, (name, line))

    def test_parity(self):
        self.assertEqual(logic.parity("1011001"), "0")
        self.assertEqual(logic.parity("1011000"), "1")


@unittest.skipUnless(shutil.which("bash"), "no bash")
class BitflipBansheeTest(unittest.TestCase):
    FIGHT, SCRIPT, TEST = "bitflip_banshee", "fix_bits.sh", "test_fix_bits.sh"

    def test_the_bent_check_fails_and_why_shows_a_word(self):
        for seed in range(12):
            tmp, work, ch, meta = arena(self.FIGHT, seed)
            with tmp, self.subTest(seed=seed):
                self.assertFalse(ch.check(work, meta, "done"))
                self.assertRegex(ch.why(work), r"[01]{7}")

    def test_the_last_hint_wins(self):
        for seed in range(12):
            tmp, work, ch, meta = arena(self.FIGHT, seed)
            with tmp, self.subTest(seed=seed):
                bash(SOLUTIONS[self.FIGHT][0], work)
                self.assertTrue(ch.check(work, meta, "done"))
                self.assertIsNone(ch.why(work))

    def test_printing_the_data_bits_without_fixing_them_loses(self):
        tmp, work, ch, meta = arena(self.FIGHT)
        with tmp:
            (work / self.SCRIPT).write_text('#!/usr/bin/env bash\nwhile read -r w; do echo "${w:2:1}${w:4:3}"; done\n')
            self.assertFalse(ch.check(work, meta, "done"))

    def test_the_small_test_fails_first_then_passes(self):
        for seed in range(6):
            tmp, work, ch, meta = arena(self.FIGHT, seed)
            with tmp, self.subTest(seed=seed):
                self.assertIn(self.TEST, ch.task)
                self.assertIn("Your turn", (work / self.TEST).read_text())
                out = bash(f"bash {self.TEST} 2>&1", work)
                self.assertIn("FAIL", out)
                self.assertIn("ok ", out)
                bash(SOLUTIONS[self.FIGHT][0], work)
                self.assertNotIn("FAIL", bash(f"bash {self.TEST} 2>&1", work))

    def test_words_txt_decodes_after_the_fix(self):
        tmp, work, ch, meta = arena(self.FIGHT)
        with tmp:
            bash(SOLUTIONS[self.FIGHT][0], work)
            bits = bash(f"bash {self.SCRIPT} < words.txt", work).split()
            text = "".join(chr(int(a + b, 2)) for a, b in zip(bits[::2], bits[1::2]))
            self.assertEqual(text, meta["message"])


@unittest.skipUnless(shutil.which("bash"), "no bash")
class ParityChestTest(unittest.TestCase):
    FIGHT = "trial_logic_parity"

    def test_or_is_not_xor(self):
        tmp, work, ch, meta = arena(self.FIGHT)
        with tmp:
            self.assertFalse(ch.check(work, meta, "done"))
            self.assertTrue(ch.why(work))
            bash(SOLUTIONS[self.FIGHT][0], work)
            self.assertTrue(ch.check(work, meta, "done"))
            self.assertIsNone(ch.why(work))
            self.assertNotIn("FAIL", bash("bash test_parity.sh 2>&1", work))


if __name__ == "__main__":
    unittest.main()
