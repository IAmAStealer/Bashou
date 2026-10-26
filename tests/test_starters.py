"""Fights you solve by writing code come with a starter (user, 2026-10-21: "python3 fights is like a small
program to make: give a small base file to help"; "at least not totally empty, some people have blank page
syndrome"). It runs as it is and leaves one step to write."""

import random
import sqlite3
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
    "percent_poltergeist": ("        print(line, end=\"\")", "        print(urllib.parse.unquote(line), end=\"\")",
                            lambda out, m: "/etc/" + m["answer"] in out),
    "token_trickster": ("print(payload)", "print(base64.urlsafe_b64decode(payload + \"==\"))",
                        lambda out, m: m["answer"] in out),
    "subnet_sprite": ("        print(address)", "        count += address in net",
                      lambda out, m: f"{m['answer']} inside" in out),
    "six_serpent": ("        print(line.strip())", "        print(ipaddress.ip_address(line.strip()))",
                    lambda out, m: out.split().count(m["answer"]) == 2),
}


class Fights(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def fight(self, cid, seed):
        work = Path(self.tmp.name) / f"{cid}-{seed}"
        work.mkdir()
        meta = challenges.BY_ID[cid].setup(work, random.Random(seed))
        return work, meta


class StarterTest(Fights):
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


class SqlStarterTest(Fights):
    """SQL fights you write from nothing start with a file too (user: "some people have blank page syndrome")."""

    def test_upsert_starts_with_an_insert_that_only_works_for_a_new_item(self):
        ch = challenges.BY_ID["upsert_unicorn"]
        for seed in range(5):
            with self.subTest(seed=seed):
                work, meta = self.fight("upsert_unicorn", seed)
                sql = (work / meta["args"]["file"]).read_text()
                self.assertIn("INSERT INTO stock", sql)
                self.assertFalse(ch.verify(work, meta, ""))
                insert = next(line for line in sql.splitlines() if line.startswith("INSERT"))
                done = insert.rstrip(";") + " ON CONFLICT(item) DO UPDATE SET qty = qty + excluded.qty;"
                (work / meta["args"]["file"]).write_text(sql.replace(insert, done))
                self.assertTrue(ch.verify(work, meta, ""))

    def test_table_troll_starts_with_an_example_to_follow(self):
        ch = challenges.BY_ID["table_troll"]
        for seed in range(5):
            with self.subTest(seed=seed):
                work, meta = self.fight("table_troll", seed)
                a = meta["args"]
                sql = (work / "create.sql").read_text()
                self.assertIn("CREATE TABLE", sql)
                self.assertIn(f"sqlite3 {a['db']} < create.sql", sql)
                db = sqlite3.connect(work / a["db"])
                db.executescript(sql)                       # the starter alone makes nothing
                db.close()
                self.assertFalse(ch.verify(work, meta, ""))
                db = sqlite3.connect(work / a["db"])
                db.executescript(sql + f"CREATE TABLE {a['table']} ({a['text']} TEXT, {a['number']} INTEGER);\n")
                db.close()
                self.assertTrue(ch.verify(work, meta, ""))

    def test_their_tasks_point_to_the_file(self):
        self.assertIn("create.sql", challenges.BY_ID["table_troll"].task)
        self.assertIn("{file} already holds", challenges.BY_ID["upsert_unicorn"].task)


if __name__ == "__main__":
    unittest.main()
