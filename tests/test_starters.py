"""Fights you solve by writing code come with a starter (user, 2026-10-21: "python3 fights is like a small
program to make: give a small base file to help"; "at least not totally empty, some people have blank page
syndrome"). It runs as it is and leaves one step to write."""

import base64
import json
import os
import random
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bashou import challenges

# fight: (line of the starter to change, what to put instead)
FINISH = {
    "json_jinn": ("print(config.keys())", "print(config[\"database\"][\"port\"])"),
    "base64_banshee": ("print(text)", "print(base64.b64decode(text).decode())"),
    "percent_poltergeist": ("        print(line, end=\"\")",
                            "        line = urllib.parse.unquote(line)\n        if \"/etc/\" in line:\n"
                            "            print(line.split(\"/etc/\")[1].split()[0])"),
    "token_trickster": ("print(payload)", "print(json.loads(base64.urlsafe_b64decode(payload + \"==\"))[\"sub\"])"),
    "subnet_sprite": ("        print(address)", "        if address in net:\n            count += 1"),
    "six_serpent": ("        print(address)",
                    "        if address in seen:\n            print(address)\n        seen.add(address)"),
}
DATA = {"json_jinn": "config.json", "base64_banshee": "secret.txt", "percent_poltergeist": "access.log",
        "token_trickster": "token.txt", "subnet_sprite": "hosts.txt", "six_serpent": "addrs.txt"}


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
    """Bug (user, 2026-11-04): these fights asked to type the answer; your program must print it, and `verify`
    runs your program."""

    def test_they_are_won_with_verify_not_by_typing_the_answer(self):
        for cid in FINISH:
            ch = challenges.BY_ID[cid]
            self.assertTrue(ch.fix, cid)
            self.assertIn("verify", ch.task, cid)
            self.assertNotIn("answer <", ch.task, cid)
            self.assertIn("solve.py", ch.task, cid)

    def test_the_starter_runs_but_does_not_win(self):
        for cid in FINISH:
            for seed in range(5):
                with self.subTest(cid, seed=seed):
                    work, meta = self.fight(cid, seed)
                    done = subprocess.run([sys.executable, "solve.py"], cwd=work, capture_output=True, text=True,
                                          timeout=30)
                    self.assertEqual(done.returncode, 0, done.stderr)
                    self.assertFalse(challenges.BY_ID[cid].check(work, meta, "done"))

    def test_finishing_the_starter_wins(self):
        for cid, (line, new) in FINISH.items():
            for seed in range(5):
                with self.subTest(cid, seed=seed):
                    work, meta = self.fight(cid, seed)
                    code = (work / "solve.py").read_text()
                    self.assertEqual(code.splitlines().count(line), 1, code)
                    (work / "solve.py").write_text(code.replace(line + "\n", new + "\n"))
                    self.assertTrue(challenges.BY_ID[cid].check(work, meta, "done"))

    def test_an_answer_typed_in_the_program_does_not_win(self):
        for cid, data in DATA.items():
            for seed in range(5):
                with self.subTest(cid, seed=seed):
                    work, meta = self.fight(cid, seed)
                    (work / "solve.py").write_text(f"print({str(meta['answer'])!r})\n")
                    (work.parent / "meta.json").write_text(json.dumps(meta))
                    ch = challenges.BY_ID[cid]
                    self.assertFalse(ch.check(work, meta, "done"))
                    self.assertIn(data, ch.why(work))

    def test_extra_output_does_not_win(self):
        for cid, (line, new) in FINISH.items():
            with self.subTest(cid):
                work, meta = self.fight(cid, 1)
                code = (work / "solve.py").read_text().replace(line + "\n", new + "\n")
                (work / "solve.py").write_text(code + 'print("done")\n')
                self.assertFalse(challenges.BY_ID[cid].check(work, meta, "done"))

    def test_the_data_file_gone_is_told_not_a_crash(self):
        for cid, data in DATA.items():
            with self.subTest(cid):
                work, meta = self.fight(cid, 1)
                (work / "solve.py").write_text(f"print({str(meta['answer'])!r})\n")
                (work / data).unlink()
                (work.parent / "meta.json").write_text(json.dumps(meta))
                self.assertFalse(challenges.BY_ID[cid].check(work, meta, "done"))
                self.assertIn(data, challenges.BY_ID[cid].why(work))

    def test_the_poltergeist_takes_the_file_with_its_path(self):
        work, meta = self.fight("percent_poltergeist", 2)
        (work / "solve.py").write_text(
            'import re, urllib.parse\n\nwith open("access.log", encoding="utf-8") as fh:\n'
            '    print(re.search(r"/etc/\\w+", urllib.parse.unquote(fh.read())).group())\n')
        self.assertTrue(challenges.BY_ID["percent_poltergeist"].check(work, meta, "done"))

    def finished(self, cid, seed=1):
        work, meta = self.fight(cid, seed)
        line, new = FINISH[cid]
        (work / "solve.py").write_text((work / "solve.py").read_text().replace(line + "\n", new + "\n"))
        (work.parent / "meta.json").write_text(json.dumps(meta))
        return challenges.BY_ID[cid], work, meta

    def test_a_folder_without_rights_does_not_crash_verify(self):
        for mode in (0o555, 0o500, 0o300, 0o100):
            with self.subTest(oct(mode)):
                ch, work, meta = self.finished("json_jinn", mode)
                work.chmod(mode)
                self.addCleanup(work.chmod, 0o755)
                if mode & 0o400:                       # readable: the answer can be read
                    self.assertTrue(ch.check(work, meta, "done"))
                else:
                    ch.check(work, meta, "done")       # no exception is all we ask

    def test_links_in_the_folder_are_not_followed(self):
        ch, work, meta = self.finished("json_jinn")
        (work / "a").symlink_to(".")
        (work / "b").symlink_to(".")
        (work / "home").symlink_to("/")
        self.assertTrue(ch.check(work, meta, "done"))

    def test_a_pipe_for_the_data_file_does_not_hang(self):
        work, meta = self.fight("json_jinn", 1)
        (work / "solve.py").write_text(f"print({meta['answer']})\n")
        (work / "config.json").unlink()
        os.mkfifo(work / "config.json")
        (work.parent / "meta.json").write_text(json.dumps(meta))
        ch = challenges.BY_ID["json_jinn"]
        self.assertFalse(ch.check(work, meta, "done"))
        self.assertIn("config.json", ch.why(work))

    def test_a_program_that_removes_itself_does_not_crash(self):
        work, meta = self.fight("json_jinn", 1)
        (work / "solve.py").write_text(f"import os\nos.remove('solve.py')\nprint({meta['answer']})\n")
        self.assertFalse(challenges.BY_ID["json_jinn"].check(work, meta, "done"))

    def test_a_crash_on_the_copy_is_told_as_a_crash(self):
        """Without the padding, half the tokens decode: the real error must show, not "doesn't read the file"."""
        ch, work, meta = self.finished("token_trickster")
        (work / "solve.py").write_text(
            'import base64, json, sys\nwith open("token.txt", encoding="utf-8") as fh:\n'
            '    claims = fh.read().split(".")[1]\n'
            f'if json.loads(base64.urlsafe_b64decode(claims + "=="))["sub"] != {meta["answer"]!r}:\n'
            '    sys.exit("Incorrect padding")\n'
            f'print({meta["answer"]!r})\n')
        self.assertFalse(ch.check(work, meta, "done"))
        self.assertIn("Incorrect padding", ch.why(work))

    def test_a_slow_refusal_does_not_run_the_program_again(self):
        ch, work, meta = self.finished("json_jinn")
        (work / "solve.py").write_text('with open("runs", "a") as f:\n    f.write("x")\n')
        (work.parent / "meta.json").write_text(json.dumps(meta))
        self.assertFalse(ch.check(work, meta, "done"))
        self.assertIn("print()", ch.why(work))
        self.assertEqual((work / "runs").read_text(), "x")

    def test_the_poltergeist_wants_nothing_else(self):
        work, meta = self.fight("percent_poltergeist", 2)
        ch = challenges.BY_ID["percent_poltergeist"]
        for out in ("The attacker wants /etc/{}", "attack found\\n/etc/{}", "nope/{}"):
            (work / "solve.py").write_text(f'print("{out.format(meta["answer"])}")\n')
            self.assertFalse(ch.check(work, meta, "done"), out)

    def test_counting_lines_does_not_win_the_sprite(self):
        work, meta = self.fight("subnet_sprite", 1)
        total = len((work / "hosts.txt").read_text().splitlines())
        (work / "solve.py").write_text(
            f'with open("hosts.txt", encoding="utf-8") as fh:\n    print(sum(1 for line in fh) - {total - meta["answer"]})\n')
        self.assertFalse(challenges.BY_ID["subnet_sprite"].check(work, meta, "done"))

    def test_the_banshee_hides_only_the_word(self):
        work, meta = self.fight("base64_banshee", 3)
        self.assertEqual(base64.b64decode((work / "secret.txt").read_text()).decode(), meta["answer"])


class JsonJinnTest(Fights):
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
