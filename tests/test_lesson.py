import json
import tempfile
import unittest
from pathlib import Path

from bashou import achievements, challenges, lesson, render, skills, state
from bashou.lesson import HERE, reader

LESSONS = lesson.load("en")
BY_ID = {le["id"]: le for le in LESSONS}


def conditions(le):
    return [c.strip() for need in le.get("needs", []) for c in need.split("|")]


class FilesTest(unittest.TestCase):
    def test_every_lesson_is_well_formed(self):
        ids = [le["id"] for le in LESSONS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len({le["order"] for le in LESSONS}), len(LESSONS))
        for path in (HERE / "en").glob("*.json"):
            self.assertEqual(json.loads(path.read_text())["id"], path.stem)
        for le in LESSONS:
            self.assertTrue(le["title"] and le["summary"] and le["pages"], le["id"])
            if "skill" in le:
                self.assertIn(le["skill"], skills.SKILLS, le["id"])

    def test_conditions_name_real_things(self):
        fights = {c.id for c in challenges.ALL}
        earned = {a.id for a in achievements.ALL}
        for le in LESSONS:
            for cond in conditions(le):
                kind, *args = cond.split()
                with self.subTest(lesson=le["id"], cond=cond):
                    if kind == "lesson":
                        self.assertIn(args[0], BY_ID)
                        self.assertLess(BY_ID[args[0]]["order"], le["order"])     # no loops, list reads in order
                        prev = BY_ID[args[0]].get("skill")
                        self.assertIn(prev, (None, le.get("skill")), "a lesson you may never see can't block it")
                    elif kind == "won":
                        self.assertIn(args[0], fights)
                    elif kind == "achievement":
                        self.assertIn(args[0], earned)
                    else:
                        lesson.met(state.default(), cond)       # raises on an unknown kind

    def test_pages_fit_an_80x24_terminal(self):
        for le in LESSONS:
            for n, page in enumerate(le["pages"]):
                with self.subTest(lesson=le["id"], page=n + 1):
                    scheme = page.get("scheme", [])
                    self.assertLessEqual(max(map(render.width, scheme), default=0), lesson.SCHEME_WIDTH)
                    self.assertLessEqual(len(scheme), lesson.SCHEME_LINES)
                    if "point" in page:
                        self.assertLess(page["point"], len(scheme))
                        self.assertTrue(scheme[page["point"]].strip())
                    for word in page.get("mark", []):
                        self.assertTrue(any(word in line for line in scheme), word)
                    pieces = reader.page_screen(le, n, 80, 200)
                    body = [row for row, col, text in pieces[:-1]]
                    self.assertLessEqual(max(body), 22, "text runs into the key line")
                    owl = [col for row, col, text in pieces if "▀" in text or "▄" in text]
                    self.assertTrue(owl, "the owl has room at 80 columns")
                    self.assertLessEqual(max(owl) + reader.OWL.width - 1, 80)

    def test_translations_match_english(self):
        for folder in HERE.iterdir():
            if not folder.is_dir() or folder.name in ("en", "__pycache__"):
                continue
            for path in folder.glob("*.json"):
                with self.subTest(lang=folder.name, lesson=path.stem):
                    local, en = json.loads(path.read_text()), BY_ID[path.stem]
                    self.assertLessEqual(set(local), {"title", "summary", "pages"})
                    self.assertEqual(len(local["pages"]), len(en["pages"]))
                    for mine, theirs in zip(local["pages"], en["pages"]):
                        self.assertEqual(mine.get("point"), theirs.get("point"))
                        self.assertEqual(len(mine.get("scheme", [])), len(theirs.get("scheme", [])))
                        self.assertLessEqual(max(map(render.width, mine.get("scheme", [])), default=0),
                                             lesson.SCHEME_WIDTH)
            for le in lesson.load(folder.name):
                for n in range(len(le["pages"])):
                    pieces = reader.page_screen(le, n, 80, 200)
                    self.assertLessEqual(max(row for row, col, text in pieces[:-1]), 22, (le["id"], n))


class UnlockTest(unittest.TestCase):
    def test_a_new_player_starts_with_the_first_lesson(self):
        s = state.default()
        self.assertEqual([le["id"] for le in lesson.new(s, LESSONS)], ["command_line"])
        paths = BY_ID["paths"]
        self.assertFalse(lesson.unlocked(s, paths))
        self.assertEqual(lesson.how_to_unlock(s, paths, {"command_line": "Reading a command line"}),
                         "read “Reading a command line”")
        s["lessons"]["read"].append("command_line")
        self.assertTrue(lesson.unlocked(s, paths))

    def test_either_side_of_a_bar_is_enough(self):
        s = state.default()
        heap = BY_ID["stack_heap"]
        self.assertFalse(lesson.unlocked(s, heap))
        self.assertIn("(0/3)", lesson.how_to_unlock(s, heap, {}))
        s["tools"]["gcc"] = 3
        self.assertTrue(lesson.unlocked(s, heap))
        s = state.default()
        s["challenges"].append("semicolon_slug")
        self.assertTrue(lesson.unlocked(s, heap))

    def test_every_lesson_can_be_unlocked(self):
        s = state.default()
        s.update(commands=10 ** 6, fights_won=100, challenges=[c.id for c in challenges.ALL],
                 achievements=[a.id for a in achievements.ALL])
        s["tools"] = {c.split()[1]: 1000 for le in LESSONS for c in conditions(le) if c.startswith("tool ")}
        s["lessons"]["read"] = list(BY_ID)
        self.assertEqual([le["id"] for le in LESSONS if not lesson.unlocked(s, le)], [])

    def test_only_the_skills_you_learn(self):
        s = state.default()
        s["skills"] = ["c"]
        ids = {le["id"] for le in lesson.shown(s, LESSONS)}
        self.assertIn("stack_heap", ids)
        self.assertIn("command_line", ids)
        self.assertNotIn("pipes", ids)
        s["lessons"]["opened"].append("pipes")                  # opened before unticking bash: it stays
        self.assertIn("pipes", {le["id"] for le in lesson.shown(s, LESSONS)})

    def test_an_old_save_gets_the_missing_fields(self):
        s = {"lessons": {"read": ["paths"]}}
        self.assertEqual(lesson.progress_of(s), {"read": ["paths"], "opened": [], "page": {}})


class ReaderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = state.DATA, state.STATE
        state.DATA = Path(self.tmp.name)
        state.STATE = state.DATA / "state.json"

    def tearDown(self):
        state.DATA, state.STATE = self.saved
        self.tmp.cleanup()

    def test_read_a_lesson_to_the_end_unlocks_the_next(self):
        lib = reader.Library(LESSONS)
        self.assertEqual(lib.lessons[lib.pos]["id"], "command_line")      # the new lesson is selected
        lib.key("enter")
        self.assertEqual(lib.lesson["id"], "command_line")
        for _ in BY_ID["command_line"]["pages"]:
            lib.key("enter")
        self.assertIsNone(lib.lesson)
        s = state.load()
        self.assertEqual(s["lessons"]["read"], ["command_line"])
        self.assertIn("The file tree and paths", lib.message)                # "New: …"
        self.assertEqual(lib.lessons[lib.pos]["id"], "paths")

    def test_a_locked_lesson_says_how_to_open_it(self):
        lib = reader.Library(LESSONS)
        lib.pos = next(i for i, le in enumerate(lib.lessons) if le["id"] == "paths")
        lib.key("enter")
        self.assertIsNone(lib.lesson)
        self.assertIn("read “Reading a command line”", lib.message)

    def test_leaving_keeps_the_page(self):
        lib = reader.Library(LESSONS, "command_line")
        lib.key("right")
        lib.key("right")
        lib.key("quit")
        self.assertIsNone(lib.lesson)
        lib.key("enter")
        self.assertEqual(lib.page, 2)
        self.assertEqual(state.load()["lessons"]["read"], [])

    def test_list_screen_draws(self):
        lib = reader.Library(LESSONS)
        text = "".join(t for r, c, t in lib.list_screen(80, 24))
        self.assertIn("Reading a command line", text)
        self.assertIn("🔒", text)


if __name__ == "__main__":
    unittest.main()
