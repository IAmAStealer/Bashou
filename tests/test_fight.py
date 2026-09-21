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
    # security
    "hidden_file": ("cat .[!.]*", None),
    "encoded_note": ("base64 -d note.txt | cut -d' ' -f2", None),
    "failed_logins": ("grep 'Failed password' auth.log | awk '{{print $(NF-3)}}' | sort | uniq -c | sort -rn"
                      " | head -1 | awk '{{print $2}}'", None),
    "recent_change": ("find site -type f -mmin -10", None),
    "cron_backdoor": ("grep -rh '| *sh' etc/cron.d | grep -oE 'https?://[^/]+' | cut -d/ -f3", None),
    "suid_file": ("find bin -perm -4000 -type f", None),
    # adventure chests
    "trial_dirs": ("mkdir -p {x}", r"folders (\S+)"),
    "trial_note": ("echo {x} > map.txt", r"the word (\w+)"),
    "trial_move": ("mv key.txt chest/", None),
    "trial_copy": ("cp -r scroll backup", None),
    "trial_rename": ("mv rusty_sword.txt shiny_sword.txt", None),
    "trial_clean": ("rm *.tmp", None),
    "trial_spell": ("chmod u+x spell.sh && ./spell.sh > /dev/null", None),
    "trial_link": ("ln -s camp/tent home", None),
    "trial_journal": ("echo rested >> journal.txt", None),
    "trial_gems": ("find cave -name '*.gem' | wc -l", None),
    "trial_loot": ("tar czf loot.tar.gz loot", None),
    "trial_letter": ("sed -i 's/dragon/friend/g' letter.txt", None),
    "trial_scrolls": ("grep -rl treasure library", None),
}


class ChallengeTest(unittest.TestCase):
    def test_every_challenge_has_a_solution(self):
        self.assertEqual(set(SOLUTIONS), set(challenges.BY_ID))

    def test_reference_solutions(self):
        for ch in challenges.ALL + challenges.SECURITY + challenges.TRIALS:
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


class TrialTest(unittest.TestCase):
    def test_doing_nothing_fails(self):
        for ch in challenges.TRIALS:
            with tempfile.TemporaryDirectory() as tmp:
                meta = ch.setup(Path(tmp), random.Random(0))
                self.assertFalse(ch.check(Path(tmp), meta, ""), ch.id)

    def test_hints_show_the_real_names(self):
        ch = challenges.BY_ID["trial_dirs"]
        meta = ch.setup(Path("."), random.Random(0))
        self.assertIn(meta["args"]["path"], ch.hint_text(1, meta))
        awk = challenges.BY_ID["failed_logins"]
        self.assertIn("{print $(NF-3)}", awk.hint_text(1, {}))     # other braces untouched


class SecurityTest(unittest.TestCase):
    def test_the_busiest_ip_is_not_the_attacker(self):
        """Counting every line gives the admin's IP (successful logins): you have to filter first."""
        ch = challenges.BY_ID["failed_logins"]
        for seed in range(5):
            with tempfile.TemporaryDirectory() as tmp:
                meta = ch.setup(Path(tmp), random.Random(seed))
                cmd = "awk '{print $(NF-3)}' auth.log | sort | uniq -c | sort -rn | head -1 | awk '{print $2}'"
                out = subprocess.run(["bash", "-c", cmd], cwd=tmp, capture_output=True, text=True).stdout.strip()
                self.assertFalse(ch.check(Path(tmp), meta, out))

    def test_security_is_never_sent_as_a_threat(self):
        s = state.default()
        s["challenges"] = [c.id for c in challenges.ALL]
        self.assertIsNone(fight.maybe_threat(s, ThreatTest.Always(), 1_800_000_000))


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
