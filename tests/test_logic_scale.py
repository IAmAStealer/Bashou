"""Logic at scale (owner, 2026-10-31): how much work a script does, shaping data once, codes that fix
themselves. Each fight hands a bash script that works on a small file and must still work on a big
hidden one, within the time limit."""

import json
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bashou import challenges
from bashou.challenges import logic

# CI for 0.12.1: macOS's grep -f takes over 5 seconds on 20 000 lines, as the hints tell players; comm is their way.
SLOW_GREP_F = sys.platform == "darwin"


def arena(fight_id, seed=0):
    tmp = tempfile.TemporaryDirectory()
    work = Path(tmp.name) / "arena"
    work.mkdir()
    ch = challenges.BY_ID[fight_id]
    meta = ch.setup(work, random.Random(seed))
    (work.parent / "meta.json").write_text(json.dumps({"challenge": fight_id, **meta}))
    return tmp, work, ch, meta


def bash(cmd, work):
    return subprocess.run(["bash", "-c", cmd], cwd=work, capture_output=True, text=True, timeout=60).stdout


@unittest.skipUnless(shutil.which("bash") and shutil.which("grep"), "no bash")
class SquareSpiderTest(unittest.TestCase):
    FIGHT, SCRIPT, TEST = "square_spider", "common.sh", "test_common.sh"
    FIXES = {
        "grep": "grep -Fxf newsletter.txt customers.txt",
        "comm": "comm -12 <(sort customers.txt) <(sort newsletter.txt)",
        "table": ('declare -A on\nwhile IFS= read -r m; do on[$m]=1; done < newsletter.txt\n'
                  'while IFS= read -r c; do\n  if [ -n "${on[$c]+x}" ]; then echo "$c"; fi\ndone < customers.txt'),
    }
    WRONG = {
        "regex": "grep -xf newsletter.txt customers.txt",            # a dot in an address matches any character
        "part": "grep -Ff newsletter.txt customers.txt",             # bo@example.org found inside jimbo@example.org
    }
    EYE, SHOWS = "regex", ("part", "@example.org")                  # fails the by-eye case; named by why

    def fixed(self, work, body):
        script = work / self.SCRIPT
        head = [line for line in script.read_text().splitlines() if line.startswith("#")]
        script.write_text("\n".join(head + [body]) + "\n")

    def test_the_nested_loops_are_too_slow_for_the_big_lists(self):
        tmp, work, ch, meta = arena(self.FIGHT)
        with tmp:
            self.assertIn("while", (work / self.SCRIPT).read_text())
            self.assertFalse(ch.check(work, meta, "done"))
            self.assertIn("5 seconds", ch.why(work))

    def test_one_pass_fixes_win(self):
        for name, body in self.FIXES.items():
            if name == "grep" and SLOW_GREP_F:
                continue
            tmp, work, ch, meta = arena(self.FIGHT)
            with tmp, self.subTest(name):
                self.fixed(work, body)
                self.assertTrue(ch.check(work, meta, "done"))
                self.assertIsNone(ch.why(work))

    def test_fast_but_wrong_is_refused_and_says_which_address(self):
        for name, body in self.WRONG.items():
            tmp, work, ch, meta = arena(self.FIGHT)
            with tmp, self.subTest(name):
                self.fixed(work, body)
                self.assertFalse(ch.check(work, meta, "done"))
                if name == self.SHOWS[0] and not SLOW_GREP_F:
                    self.assertIn(self.SHOWS[1], ch.why(work))
                else:                                        # 20 000 regexes: wrong, and grep is slow on them too
                    self.assertTrue(ch.why(work))

    def test_the_small_test_checks_by_eye_and_times_doubling_lists(self):
        tmp, work, ch, meta = arena(self.FIGHT)
        with tmp:
            self.assertIn(self.TEST, ch.task)
            text = (work / self.TEST).read_text()
            self.assertIn("Your turn", text)
            out = bash(f"bash {self.TEST} 2>&1", work)
            self.assertIn("ok ", out)                      # slow, but right
            self.assertEqual(out.count(" s\n"), 3)         # three timings
            self.fixed(work, self.WRONG[self.EYE])
            self.assertIn("FAIL", bash(f"bash {self.TEST} 2>&1", work))
            self.fixed(work, next(iter(self.FIXES.values())))
            self.assertNotIn("FAIL", bash(f"bash {self.TEST} 2>&1", work))

    def test_the_players_lists_are_slow_enough_to_feel(self):
        tmp, work, ch, meta = arena(self.FIGHT)
        with tmp:
            n = len((work / "customers.txt").read_text().splitlines())
            self.assertGreaterEqual(n, 800)
            self.assertTrue(set((work / "customers.txt").read_text().split())
                            & set((work / "newsletter.txt").read_text().split()))


class SquareChestTest(SquareSpiderTest):
    FIGHT, SCRIPT, TEST = "trial_logic_missing", "missing.sh", "test_missing.sh"
    FIXES = {
        "grep": "grep -vFxf present.txt team.txt",
        "comm": "comm -23 <(sort team.txt) <(sort present.txt)",
    }
    WRONG = {
        "regex": "grep -vxf present.txt team.txt",
        "part": "grep -vFf present.txt team.txt",
    }

    def test_the_players_lists_are_slow_enough_to_feel(self):
        tmp, work, ch, meta = arena(self.FIGHT)
        with tmp:
            self.assertGreaterEqual(len((work / "team.txt").read_text().splitlines()), 800)


class ParseParrotTest(SquareSpiderTest):
    FIGHT, SCRIPT, TEST = "parse_parrot", "bill.sh", "test_bill.sh"
    FIXES = {
        "table": ("declare -A price\nwhile read -r item cents; do price[$item]=$cents; done < prices.txt\n"
                  "while read -r customer item qty; do\n  echo \"$customer $item $((price[$item] * qty))\"\n"
                  "done < orders.txt"),
        "awk": "awk 'NR == FNR { price[$1] = $2; next } { print $1, $2, price[$2] * $3 }' prices.txt orders.txt",
    }
    WRONG = {
        "swap": "awk 'NR == FNR { price[$1] = $2; next } { print $1, $2, price[$2] * $3 }' orders.txt prices.txt",
        "prefix": ("declare -A price\nwhile read -r item cents; do price[${item%%-*}]=$cents; done < prices.txt\n"
                   "while read -r customer item qty; do\n  echo \"$customer $item $((price[${item%%-*}] * qty))\"\n"
                   "done < orders.txt"),                          # tea-xl isn't tea
    }
    EYE, SHOWS = "swap", ("prefix", " tea ")

    def test_the_players_lists_are_slow_enough_to_feel(self):
        tmp, work, ch, meta = arena(self.FIGHT)
        with tmp:
            self.assertGreaterEqual(len((work / "orders.txt").read_text().splitlines()), 800)
            items = {line.split()[0] for line in (work / "prices.txt").read_text().splitlines()}
            self.assertTrue(all(line.split()[1] in items for line in (work / "orders.txt").read_text().splitlines()))


class ParrotChestTest(SquareSpiderTest):
    FIGHT, SCRIPT, TEST = "trial_logic_shelf", "shelf.sh", "test_shelf.sh"
    FIXES = {
        "table": ("declare -A shelf\nwhile read -r item place; do shelf[$item]=$place; done < shelves.txt\n"
                  "while read -r order item; do\n  echo \"$order $item ${shelf[$item]}\"\ndone < picks.txt"),
        "awk": "awk 'NR == FNR { shelf[$1] = $2; next } { print $1, $2, shelf[$2] }' shelves.txt picks.txt",
    }
    WRONG = {
        "swap": "awk 'NR == FNR { shelf[$1] = $2; next } { print $1, $2, shelf[$2] }' picks.txt shelves.txt",
        "prefix": ("declare -A shelf\nwhile read -r item place; do shelf[${item%%-*}]=$place; done < shelves.txt\n"
                   "while read -r order item; do\n  echo \"$order $item ${shelf[${item%%-*}]}\"\ndone < picks.txt"),
    }
    EYE, SHOWS = "swap", ("prefix", " tea ")

    def test_the_players_lists_are_slow_enough_to_feel(self):
        tmp, work, ch, meta = arena(self.FIGHT)
        with tmp:
            self.assertGreaterEqual(len((work / "picks.txt").read_text().splitlines()), 800)


class HiddenListsTest(unittest.TestCase):
    def test_the_hidden_lists_hold_the_traps(self):
        a, b = logic.big_lists(random.Random(1))
        self.assertGreaterEqual(min(len(a), len(b)), 20000)
        self.assertEqual(len(a), len(set(a)))
        self.assertIn("ana-b@example.org", a)
        self.assertIn("ana.b@example.org", b)
        self.assertIn("jimbo@example.org", a)
        self.assertIn("bo@example.org", b)
        self.assertNotIn("bo@example.org", a)

    def test_the_hidden_orders_hold_items_that_start_alike(self):
        files, want = logic.bill_files(random.Random(1))
        self.assertGreaterEqual(len(files["orders.txt"]), 20000)
        items = [line.split()[0] for line in files["prices.txt"]]
        self.assertIn("tea", items)
        self.assertIn("tea-xl", items)
        self.assertEqual(len(want), len(files["orders.txt"]))


if __name__ == "__main__":
    unittest.main()


class MacReferenceTest(unittest.TestCase):
    def test_reference_solutions_do_not_rely_on_grep_f(self):
        """CI for 0.12.1 failed on macOS: the reference solutions used grep -f, too slow there on 20 000 lines."""
        from tests.test_fight import SOLUTIONS
        for fight in ("square_spider", "trial_logic_missing"):
            self.assertNotIn("xf ", SOLUTIONS[fight][0])
            self.assertIn("comm -", SOLUTIONS[fight][0])
