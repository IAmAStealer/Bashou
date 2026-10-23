"""The SQL Bashou shows follows doc/contributing/sql-style.md (owner, 2026-10-23: the same rules pipeline as
bash). Every full statement a lesson, the owl, a question or a fight shows runs on the fight tables (EXPLAIN:
parsed and checked, never executed); the text never teaches the habits the rules forbid; our own Python passes
values to SQLite as parameters."""

import ast
import json
import random
import re
import shlex
import sqlite3
import tempfile
import unittest
from pathlib import Path

from bashou import challenges, lesson
from bashou.adventure import lessons as owl
from bashou.challenges import sql as fights

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "bashou" / "adventure" / "questions"
STATEMENT = re.compile(r"\b(?:SELECT|INSERT|UPDATE|DELETE|CREATE TABLE|WITH)\b[^;]*;")
# A sample that breaks a rule to show the mistake: where -> the rules it breaks.
ON_PURPOSE = {
    "sql-1-09": {"Q3"},         # UPDATE without WHERE: the question is what it does
}


def fixture(path):
    """The tables samples talk about: the fight databases, plus the few the questions name."""
    work = path.parent
    fights.make_shop(work, random.Random(0))
    (work / "shop.db").rename(path)
    db = sqlite3.connect(path)
    db.executescript("CREATE TABLE stock (item TEXT PRIMARY KEY, qty INTEGER NOT NULL, shelf TEXT);"
                     "CREATE TABLE movies (title TEXT, year INTEGER);"
                     "CREATE TABLE books (title TEXT, year INTEGER);"
                     "CREATE TABLE loot (item TEXT, rarity TEXT, gold INTEGER);"
                     "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, last_login TEXT);")
    db.close()


def sql_of(example):
    """The SQL in an example line: the argument of a sqlite3 command, or the line itself."""
    line = example.removeprefix("$ ").strip()
    if line.startswith("sqlite3 "):
        args = shlex.split(line)[2:]
        return " ".join(a for a in args if not a.startswith("."))
    return line


def statements(text):
    """Full statements in a text: prose around them is cut at ". " and ": " outside quotes; "SELECT …;" is a
    fragment."""
    found = []
    for part in re.split(r"(?:\.|:)\s+(?=(?:[^']*'[^']*')*[^']*$)", text):
        found += [m.group(0) for m in STATEMENT.finditer(part) if "…" not in m.group(0)]
    return found


def broken_rules(stmt, context=""):
    """The ids of sql-style.md rules a full statement breaks (the ones a regex can see)."""
    s = " ".join(stmt.split())
    found = set()
    if '"' in s:
        found.add("Q1")
    if re.search(r"(=|!=|<>)\s*NULL\b", s, re.I):
        found.add("Q2")
    if re.match(r"(UPDATE|DELETE)\b", s, re.I) and not re.search(r"\bWHERE\b", s, re.I):
        found.add("Q3")
    if re.search(r"\bINSERT(\s+OR\s+\w+)?\s+INTO\s+\w+\s+(VALUES|SELECT)\b", s, re.I):
        found.add("Q4")
    if re.search(r"\bFROM\s+\w+\s*,", s, re.I):
        found.add("Q5")
    if re.search(r"\bLIMIT\b", s, re.I) and not re.search(r"\bORDER\s+BY\b", s, re.I):
        found.add("Q7")
    if re.search(r"\bRETURNING\b|\bSTRICT\b|->>?|\bDROP\s+COLUMN\b", s, re.I) and not re.search(r"3\.3[5-9]", context):
        found.add("Q11")
    return found


def lesson_pages(lang="en"):
    """(lesson, page, number, the page's "sql") of the SQL lessons; a translation draws the English list."""
    english = {le["id"]: le for le in lesson.load("en")}
    for le in lesson.load(lang):
        if le.get("skill") != "sql":
            continue
        for n, page in enumerate(le["pages"], 1):
            yield le, page, n, english[le["id"]]["pages"][n - 1].get("sql", [])


def samples(lang="en"):
    """(where, statement, context) of every full SQL statement players see."""
    for le, page, n, listed in lesson_pages(lang):
        text = "\n".join(page.get("scheme", []) + page.get("text", []))
        for stmt in listed:
            yield f"{le['id']}/{n}", stmt, text
    for le in owl.LESSONS:
        if le["id"] == "sql":
            for n, (text, example) in enumerate(le["pages"], 1):
                for stmt in statements(sql_of(example)):
                    yield f"owl sql/{n}", stmt, text
    path = QUESTIONS / lang / "sql.json"
    for q in json.loads(path.read_text()):
        right = q["choices"][q["answer"]]
        for stmt in statements(right) + statements(q["explain"]):
            yield q["id"], stmt, q["explain"]


def fight_samples(seeds=range(2)):
    """(fight id, statement, work folder) of the SQL a fight's task, hints and starter files show."""
    for c in challenges.ALL + challenges.TRIALS:
        if "sqlite3" not in (*c.tools, *(c.requires or ())):
            continue
        for seed in seeds:
            with tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                meta = c.setup(work, random.Random(seed))
                shown = [c.task_text(meta), *c.hint_list(meta)]
                shown += [p.read_text() for p in work.glob("*.sql")]
                for text in shown:
                    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("--"))
                    for stmt in statements(code):
                        yield c.id, stmt, work


def runs(db, stmt):
    """None when SQLite accepts the statement (prepared on db, not run), else its error."""
    stmt = stmt.removesuffix(";")
    try:
        if re.match(r"CREATE TABLE", stmt, re.I):
            con = sqlite3.connect(":memory:")
            try:
                con.execute("EXPLAIN " + stmt)
            finally:
                con.close()
        else:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            try:
                con.execute("EXPLAIN " + stmt)
            finally:
                con.close()
    except sqlite3.Error as e:
        return str(e)
    return None


class StatementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.tmp.name) / "fixture.db"
        fixture(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_there_are_samples(self):
        where = {w.split("/")[0] for w, _, _ in samples()}
        self.assertTrue({"sql_select", "sql_join", "sql_write", "owl sql", "sql-1-05"} <= where, where)

    def test_every_statement_runs_on_the_fight_tables(self):
        for lang in ("en", "fr"):
            for where, stmt, _ in samples(lang):
                with self.subTest(lang, where=where, sql=stmt):
                    self.assertIsNone(runs(self.db, stmt))

    def test_every_statement_follows_the_rules(self):
        for lang in ("en", "fr"):
            for where, stmt, context in samples(lang):
                with self.subTest(lang, where=where, sql=stmt):
                    self.assertLessEqual(broken_rules(stmt, context), ON_PURPOSE.get(where, set()))

    def test_fight_sql_runs_on_its_own_database(self):
        for cid, stmt, work in fight_samples():
            with self.subTest(cid, sql=stmt):
                db = next(work.glob("*.db"), None)
                if db is None:                  # a fight that makes the database: CREATE only
                    self.assertRegex(stmt, r"^CREATE TABLE")
                self.assertIsNone(runs(db, stmt) if db else runs(self.db, stmt))
                self.assertEqual(broken_rules(stmt), set())

    def test_the_rule_checks_catch_their_mistake(self):
        for stmt, rule in [('SELECT * FROM products WHERE name = "mug";', "Q1"),
                           ("SELECT * FROM products WHERE stock = NULL;", "Q2"),
                           ("UPDATE products SET price = 0;", "Q3"),
                           ("INSERT INTO stock VALUES ('mug', 3, 'A1');", "Q4"),
                           ("SELECT * FROM orders, customers WHERE orders.customer_id = customers.id;", "Q5"),
                           ("SELECT name FROM products LIMIT 3;", "Q7"),
                           ("INSERT INTO stock (item, qty) VALUES ('mug', 3) RETURNING qty;", "Q11")]:
            with self.subTest(rule):
                self.assertIn(rule, broken_rules(stmt))
        self.assertEqual(broken_rules("SELECT name FROM products WHERE stock IS NULL;"), set())
        self.assertEqual(broken_rules("SELECT name FROM products ORDER BY price LIMIT 3;"), set())


class PromptTest(unittest.TestCase):
    """QP3 (sql-judge 2026-10-23): a line drawn after "$ " is typed in the shell, so SQL there goes through sqlite3."""

    def test_shell_lines_never_start_with_sql(self):
        bare = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|FROM|ON|WHERE)\b")
        for lang in ("en", "fr"):
            for le, page, n, _ in lesson_pages(lang):
                for t in page.get("text", []):
                    if t.startswith("$ "):
                        with self.subTest(lang, lesson=le["id"], page=n, line=t):
                            self.assertNotRegex(t[2:], bare)
        for le in owl.LESSONS:
            if le["id"] == "sql":
                for n, (_text, example) in enumerate(le["pages"], 1):
                    with self.subTest("owl", page=n):
                        self.assertNotRegex(example, bare, "the owl shows it as $ …: wrap it in sqlite3")


class FightCodeTest(unittest.TestCase):
    def test_a_folder_with_odd_characters_still_opens(self):
        """QC5: the URI is built with as_uri(): '#', '?' and '%' in a folder name broke every verify."""
        for name in ("we#ird?dir", "pct%41dir"):
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp) / name
                work.mkdir()
                fights.make_shop(work, random.Random(0))
                self.assertTrue(fights.all_products(work))

    def test_an_endless_query_is_stopped(self):
        """QC6: the player's file runs with a time limit; a recursive CTE without end hung verify."""
        import time
        start = time.monotonic()
        endless = "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) SELECT count(*) FROM c;"
        self.assertIsNone(fights.run_on_copy(endless, [("mug", 3, "A1")]))
        self.assertLess(time.monotonic() - start, 10)


class SpotTest(unittest.TestCase):
    def test_spot_sql_follows_the_rules(self):
        from bashou import spot
        for stmt in spot.SQL:
            with self.subTest(stmt):
                self.assertEqual(broken_rules(stmt) - {"Q7"}, set())


class LessonPageTest(unittest.TestCase):
    """Lesson pages list the full statements they draw ("sql"), so the test can run them."""

    def test_pages_that_draw_sql_list_it(self):
        for le in lesson.load("en"):
            if le.get("skill") != "sql":
                continue
            for n, page in enumerate(le["pages"], 1):
                drawn = page.get("scheme", []) + [t for t in page.get("text", []) if t.startswith("$ ")]
                if any(re.match(r"\s*(\$ |sqlite> )?(SELECT|INSERT|UPDATE|DELETE|CREATE)\b", d) for d in drawn):
                    with self.subTest(le["id"], page=n):
                        self.assertTrue(page.get("sql"), "add the page's full statements to its \"sql\" field")

    def test_listed_sql_is_drawn_on_its_page(self):
        token = re.compile(r"[\w.*']+|[^\s\w]")
        for lang in ("en", "fr"):
            for le, page, n, listed in lesson_pages(lang):
                drawn = token.findall("\n".join(page.get("scheme", []) + page.get("text", [])))
                for stmt in listed:
                    with self.subTest(lang, lesson=le["id"], page=n, sql=stmt):
                        it = iter(drawn)
                        self.assertTrue(all(t in it for t in token.findall(stmt)),
                                        "the page shows the statement it checks, in that order")


class OurCodeTest(unittest.TestCase):
    """Our Python gives values to SQLite as parameters (QC1) and names columns (Q4, QC2)."""

    def calls(self):
        for path in sorted((ROOT / "bashou").rglob("*.py")):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr in ("execute", "executemany", "executescript") and node.args):
                    yield path.relative_to(ROOT), node.lineno, node.args[0]

    def test_no_sql_is_built_from_strings(self):
        for path, line, arg in self.calls():
            built = (isinstance(arg, ast.JoinedStr) and any(isinstance(v, ast.FormattedValue) for v in arg.values)
                     or isinstance(arg, ast.BinOp)
                     or isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr == "format")
            with self.subTest(f"{path}:{line}"):
                self.assertFalse(built, "QC1: pass values as ? parameters")

    def test_our_sql_follows_the_rules(self):
        for path, line, arg in self.calls():
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                for stmt in [arg.value]:
                    with self.subTest(f"{path}:{line}"):
                        self.assertEqual(broken_rules(stmt + ";") & {"Q1", "Q2", "Q3", "Q4", "Q5", "Q7"}, set())
                        self.assertNotRegex(stmt, r"SELECT\s+\*", "QC2: name the columns you read")


if __name__ == "__main__":
    unittest.main()
