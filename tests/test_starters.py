"""Fights you solve by writing code come with a starter (user, 2026-10-21: "python3 fights is like a small
program to make: give a small base file to help"; "at least not totally empty, some people have blank page
syndrome"). It runs as it is and leaves one step to write."""

import json
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


class JsonJinnTest(Fights):
    """Bug (user, 2026-11-04): the JSON Jinn asked to type the port by hand; like the other programming
    fights, your program must print it, and `verify` runs your program."""

    def finish(self, work, line):
        code = (work / "solve.py").read_text()
        (work / "solve.py").write_text(code.replace("print(config.keys())", line))

    def why(self, work, meta):
        (work.parent / "meta.json").write_text(json.dumps(meta))      # where the fight keeps it
        return self.ch.why(work)

    def setUp(self):
        super().setUp()
        self.ch = challenges.BY_ID["json_jinn"]

    def test_it_is_won_with_verify_not_by_typing_the_port(self):
        self.assertTrue(self.ch.fix)
        self.assertIn("verify", self.ch.task)
        self.assertNotIn("answer <", self.ch.task)

    def test_the_starter_as_given_does_not_win(self):
        work, meta = self.fight("json_jinn", 1)
        self.assertFalse(self.ch.check(work, meta, "done"))
        self.assertIn("port", self.why(work, meta))

    def test_a_program_that_prints_the_port_wins(self):
        for seed in range(5):
            with self.subTest(seed=seed):
                work, meta = self.fight("json_jinn", seed)
                self.finish(work, 'print(config["database"]["port"])')
                self.assertTrue(self.ch.check(work, meta, "done"))
                self.assertIsNone(self.why(work, meta))

    def test_a_port_typed_in_the_program_does_not_win(self):
        work, meta = self.fight("json_jinn", 2)
        self.finish(work, f"print({meta['answer']})")
        self.assertFalse(self.ch.check(work, meta, "done"))
        self.assertIn("config.json", self.why(work, meta))

    def test_the_wrong_section_does_not_win(self):
        work, meta = self.fight("json_jinn", 3)
        self.finish(work, 'print(config["cache"]["port"])')
        self.assertFalse(self.ch.check(work, meta, "done"))

    def test_reading_the_file_line_by_line_wins(self):
        work, meta = self.fight("json_jinn", 4)
        (work / "solve.py").write_text(
            'lines = open("config.json", encoding="utf-8").read().splitlines()\n'
            'at = next(i for i, line in enumerate(lines) if "database" in line)\n'
            'part = next(line for line in lines[at:] if "port" in line)\n'
            'print(part.split(":")[1].strip(" ,"))\n')
        self.assertTrue(self.ch.check(work, meta, "done"), self.why(work, meta))

    def test_a_second_file_of_the_player_wins(self):
        work, meta = self.fight("json_jinn", 5)
        (work / "helper.py").write_text(
            'import json\nwith open("config.json", encoding="utf-8") as f:\n'
            '    port = json.load(f)["database"]["port"]\n')
        (work / "solve.py").write_text("from helper import port\nprint(port)\n")
        self.assertTrue(self.ch.check(work, meta, "done"), self.why(work, meta))

    def test_printing_nothing_is_told_plainly(self):
        work, meta = self.fight("json_jinn", 6)
        self.finish(work, 'port = config["database"]["port"]')
        self.assertFalse(self.ch.check(work, meta, "done"))
        self.assertIn("print()", self.why(work, meta))

    def test_bytes_that_are_not_text_do_not_crash(self):
        work, meta = self.fight("json_jinn", 7)
        self.finish(work, 'import sys; sys.stdout.buffer.write(b"\\xff")')
        self.assertFalse(self.ch.check(work, meta, "done"))
        self.assertIn("port", self.why(work, meta))

    def test_extra_words_do_not_win(self):
        work, meta = self.fight("json_jinn", 3)
        self.finish(work, 'print("port", config["database"]["port"])')
        self.assertFalse(self.ch.check(work, meta, "done"))

    def test_a_broken_or_missing_program_is_refused_with_a_reason(self):
        work, meta = self.fight("json_jinn", 4)
        self.finish(work, "print(")
        self.assertFalse(self.ch.check(work, meta, "done"))
        self.assertIn("python3 solve.py", self.why(work, meta))
        (work / "solve.py").unlink()
        self.assertFalse(self.ch.check(work, meta, "done"))
        self.assertIn("solve.py", self.why(work, meta))


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
