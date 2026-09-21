import random
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from bashou import challenges, fight, state

# Reference solutions, run with bash in the arena folder. {x} is filled from the task text.
SOLUTIONS = {
    "grep_hydra": ("grep -cF '[ERROR]' app.log", None),
    "awk_golem": ("awk -F, '$2 == \"{x}\" {{ s += $3 }} END {{ print s }}' sales.csv", r'for "(\w+)"'),
    "find_wraith": ("find maze -type f -name '*.bak' | wc -l", None),
    "uniq_swarm": ("sort visitors.txt | uniq -c | sort -rn | head -1 | awk '{{print $2}}'", None),
    "sed_serpent": ("sed -i 's/teh/the/g; s/Teh/The/g' letter.txt", None),
    "ps_phantom": ("pgrep -f '^{x}'", r"named (phantom-\w+)"),
    "pipe_eel": ("grep ' 404$' access.log | cut -d' ' -f1 | sort -u | wc -l", None),
}


class ChallengeTest(unittest.TestCase):
    def test_every_challenge_has_a_solution(self):
        self.assertEqual(set(SOLUTIONS), set(challenges.BY_ID))

    def test_reference_solutions(self):
        for ch in challenges.ALL:
            if not ch.available():
                continue
            for seed in range(3):
                with self.subTest(ch.id, seed=seed), tempfile.TemporaryDirectory() as tmp:
                    work = Path(tmp)
                    meta = ch.setup(work, random.Random(seed))
                    try:
                        cmd, pattern = SOLUTIONS[ch.id]
                        if pattern:
                            cmd = cmd.format(x=re.search(pattern, ch.task_text(meta)).group(1))
                        else:
                            cmd = cmd.format()
                        out = subprocess.run(["bash", "-c", cmd], cwd=work, capture_output=True,
                                             text=True).stdout.strip()
                        self.assertTrue(ch.check(work, meta, out or "done"), f"{ch.id}: {out!r}")
                        self.assertFalse(ch.check(work, {**meta, "expected": "nope"}, "wrong")
                                         and ch.verify is None)
                    finally:
                        if ch.cleanup:
                            ch.cleanup(meta)

    def test_the_pipe_eel_needs_a_real_pipeline(self):
        with tempfile.TemporaryDirectory() as base:
            ch = challenges.BY_ID["pipe_eel"]
            log = Path(base) / "log"
            log.write_text("0\t    1  grep 404 access.log | wc -l\n")          # only 2 commands
            self.assertFalse(fight.used_tool(base, ch))
            log.write_text(log.read_text() + "0\t    2  grep ' 404$' access.log | cut -d' ' -f1 | sort -u\n")
            self.assertTrue(fight.used_tool(base, ch))

    def test_the_tool_is_required(self):
        with tempfile.TemporaryDirectory() as base:
            ch = challenges.BY_ID["grep_hydra"]
            log = Path(base) / "log"
            log.write_text("0\t    1  cat app.log\n1\t    2  grep -c ERROR nope\n")
            self.assertFalse(fight.used_tool(base, ch))
            log.write_text(log.read_text() + "0\t    3  grep -c ERROR app.log | head\n")
            self.assertTrue(fight.used_tool(base, ch))


class ThreatTest(unittest.TestCase):
    class Always:
        def random(self):
            return 0.0

        def choice(self, pool):
            return pool[0]

    def test_threat_rules(self):
        s = state.default()
        now = 1_800_000_000
        note = fight.maybe_threat(s, self.Always(), now)
        self.assertIn("is coming", note)
        self.assertIsNotNone(fight.active_threat(s, now))
        # Only one at a time, and at least 2 h between two threats.
        self.assertIsNone(fight.maybe_threat(s, self.Always(), now + 60))
        self.assertIsNone(fight.maybe_threat(s, self.Always(), now + 3600))
        self.assertIsNone(fight.active_threat(s, now + 3600))    # it left after 10 min
        self.assertIsNotNone(fight.maybe_threat(s, self.Always(), now + 2 * 3600 + 1))

    def test_no_threat_when_bank_is_empty(self):
        s = state.default()
        s["challenges"] = [c.id for c in challenges.ALL]
        self.assertEqual(fight.threats_per_day(s), 0)
        self.assertIsNone(fight.maybe_threat(s, self.Always(), 1_800_000_000))

    def test_fewer_threats_at_higher_level(self):
        s = state.default()
        self.assertEqual(fight.threats_per_day(s), 3)
        s["pets"] = ["cat", "frog", "fox", "owl", "mole", "snake", "ghost", "ant", "turtle"]
        self.assertEqual(fight.threats_per_day(s), 1)


if __name__ == "__main__":
    unittest.main()
