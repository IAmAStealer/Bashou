"""Python fights you solve by writing a small program come with a starter, solve.py (user, 2026-10-21:
"python3 fights is like a small program to make: give a small base file to help"). It runs as it is,
shows the data, and leaves one step to write."""

import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bashou import challenges

# fight: (line of the starter to change, what to put instead, has it won? (output, meta))
FINISH = {
    "json_jinn": ("print(config.keys())", "print(config[\"database\"][\"port\"])",
                  lambda out, m: str(m["answer"]) in out.split()),
    "base64_banshee": ("print(text)", "print(base64.b64decode(text).decode())",
                       lambda out, m: m["answer"] in out),
    "percent_poltergeist": ("    print(line, end=\"\")", "    print(urllib.parse.unquote(line), end=\"\")",
                            lambda out, m: "/etc/" + m["answer"] in out),
    "token_trickster": ("print(payload)", "print(base64.urlsafe_b64decode(payload + \"==\"))",
                        lambda out, m: m["answer"] in out),
    "subnet_sprite": ("    print(address)", "    count += address in net",
                      lambda out, m: f"{m['answer']} inside" in out),
    "six_serpent": ("    print(line.strip())", "    print(ipaddress.ip_address(line.strip()))",
                    lambda out, m: out.split().count(m["answer"]) == 2),
}


class StarterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def fight(self, cid, seed):
        work = Path(self.tmp.name) / f"{cid}-{seed}"
        work.mkdir()
        meta = challenges.BY_ID[cid].setup(work, random.Random(seed))
        return work, meta

    def run_solve(self, work):
        done = subprocess.run([sys.executable, "solve.py"], cwd=work, capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def test_the_starter_runs_but_leaves_the_answer_to_you(self):
        for cid, (_line, _new, won) in FINISH.items():
            for seed in range(5):
                with self.subTest(cid, seed=seed):
                    work, meta = self.fight(cid, seed)
                    self.assertFalse(won(self.run_solve(work), meta))

    def test_finishing_the_starter_wins(self):
        for cid, (line, new, won) in FINISH.items():
            for seed in range(5):
                with self.subTest(cid, seed=seed):
                    work, meta = self.fight(cid, seed)
                    code = (work / "solve.py").read_text()
                    self.assertEqual(code.splitlines().count(line), 1, code)
                    (work / "solve.py").write_text(code.replace(line + "\n", new + "\n"))
                    self.assertTrue(won(self.run_solve(work), meta))

    def test_the_task_points_to_the_starter(self):
        for cid in FINISH:
            self.assertIn("solve.py", challenges.BY_ID[cid].task, cid)


if __name__ == "__main__":
    unittest.main()
