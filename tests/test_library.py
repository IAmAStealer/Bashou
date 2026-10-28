"""Owner bug report, 2026-10-27: sections came twice, nothing was locked anymore, git sat in First steps,
systemd was a skill of its own. Now: each section once, a lock level per lesson, a short path view first
(`f` for the whole library), systemd inside Linux."""

import tempfile
import unittest
from pathlib import Path

from bashou import achievements, challenges, lesson, render, skills, state
from bashou.adventure import quiz, world
from bashou.lesson import reader

LESSONS = lesson.load("en")
BY_ID = {le["id"]: le for le in LESSONS}


class Saved(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = state.DATA, state.STATE
        state.DATA = Path(self.tmp.name)
        state.STATE = state.DATA / "state.json"

    def tearDown(self):
        state.DATA, state.STATE = self.saved
        self.tmp.cleanup()

    def headers(self, lib, lines=400):
        return [render.strip(t) for r, c, t in lib.list_screen(100, lines) if c == 2 and r > 3]


class SectionTest(Saved):
    def full(self):
        with state.locked() as s:
            s["skills"] = "all"
        lib = reader.Library(LESSONS)
        lib.key("f")
        self.assertTrue(lib.full)
        return lib

    def test_each_section_shows_once(self):
        lib = self.full()
        names = [reader.group(le) for le in lib.lessons]
        runs = [n for i, n in enumerate(names) if i == 0 or names[i - 1] != n]
        self.assertEqual(len(runs), len(set(runs)), runs)

    def test_first_steps_then_git_then_the_skills(self):
        lib = self.full()
        runs = []
        for le in lib.lessons:
            if not runs or runs[-1] != reader.section(le):
                runs.append(reader.section(le))
        self.assertEqual(runs[:2], ["first", "git"])
        self.assertEqual(runs[2:], [k for k in skills.SKILLS if k in runs])

    def test_git_has_its_own_section(self):
        self.assertEqual(reader.group(BY_ID["git"]), "Git")
        self.assertNotIn("skill", BY_ID["git"])                  # open to every player

    def test_inside_a_section_lessons_keep_their_order(self):
        lib = self.full()
        for key in {reader.section(le) for le in lib.lessons}:
            orders = [le["order"] for le in lib.lessons if reader.section(le) == key]
            self.assertEqual(orders, sorted(orders), key)


class LockLevelTest(unittest.TestCase):
    def test_levels_are_known(self):
        for le in LESSONS:
            self.assertIn(le.get("opens", "passed"), ("read", "passed", "mastered"), le["id"])

    def test_the_first_steps_open_once_read(self):
        s = state.default()
        self.assertFalse(lesson.unlocked(s, BY_ID["help"]))
        s["lessons"]["read"].append("command_line")
        self.assertTrue(lesson.unlocked(s, BY_ID["help"]))
        self.assertEqual(reader.how_to_unlock(state.default(), BY_ID["help"]).split(" (")[0],
                         "read “Reading a command line”")

    def test_a_read_lesson_also_opens_when_the_one_before_is_passed(self):
        s = state.default()
        s["achievements"].append("exit_code")                  # command_line passed, not read
        self.assertTrue(lesson.unlocked(s, BY_ID["help"]))

    def test_hard_lessons_wait_for_mastery_not_for_a_count(self):
        """46 achievements opened 60 of 67 lessons on the owner's save."""
        s = state.default()
        s["achievements"] = [a.id for a in achievements.ALL]
        for hard in ("pointers", "debugger", "certs_ca", "awk_sed", "sql_join"):
            with self.subTest(hard):
                self.assertEqual(BY_ID[hard].get("opens"), "mastered")
                self.assertFalse(lesson.unlocked(s, BY_ID[hard]))
        s["challenges"] += ["leak_lurker", "stack_specter"]     # stack_heap mastered
        self.assertTrue(lesson.unlocked(s, BY_ID["pointers"]))

    def test_a_locked_hard_lesson_says_master(self):
        s = state.default()
        s["challenges"].append("leak_lurker")
        self.assertIn("master “The stack and the heap”: beat the Stack Specter in a fight",
                      reader.how_to_unlock(s, BY_ID["pointers"]).replace(BY_ID["stack_heap"]["title"],
                                                                         "The stack and the heap"))
        text = " ".join(p for p, _c in reader.unlock_lines(s, BY_ID["pointers"], 100))
        self.assertIn("mastered", text)

    def test_the_count_still_passes_a_normal_lesson(self):
        s = state.default()
        s["achievements"] = [a.id for a in achievements.ALL]
        self.assertNotIn("opens", BY_ID["regex"])
        self.assertTrue(lesson.unlocked(s, BY_ID["regex"]))

    def test_the_owners_save_has_locks_again(self):
        s = state.default()
        s["achievements"] = [a.id for a in achievements.ALL][:46]
        locked = [le for le in lesson.shown(s, LESSONS) if lesson.status(s, le) == "locked"]
        self.assertGreaterEqual(len(locked), 10)


class PathTest(Saved):
    def test_the_library_opens_on_your_path(self):
        lib = reader.Library(LESSONS)
        self.assertFalse(lib.full)
        self.assertLessEqual(len(lib.lessons), reader.PATH)
        self.assertEqual(lib.lessons[0]["id"], "command_line")
        self.assertTrue(any(lesson.status(lib.s, le) == "locked" for le in lib.lessons), "what comes next shows")
        screen = " ".join(render.strip(t) for r, c, t in lib.list_screen(100, 40))
        self.assertIn("First steps", screen)                     # each row names its section
        self.assertIn("[f] switch", screen)

    def test_f_toggles_the_whole_library(self):
        lib = reader.Library(LESSONS)
        at = lib.lessons[lib.pos]["id"]
        lib.key("f")
        self.assertTrue(lib.full)
        self.assertEqual(len(lib.lessons), len(lesson.shown(lib.s, lib.all)))
        self.assertEqual(lib.lessons[lib.pos]["id"], at)         # the cursor stays on its lesson
        screen = " ".join(render.strip(t) for r, c, t in lib.list_screen(100, 40))
        self.assertIn("[f] switch", screen)
        lib.key("f")
        self.assertFalse(lib.full)

    def test_the_two_views_show_as_tabs_the_current_one_lit(self):
        """Owner, 2026-10-27: f must stand out, and the player must see which view is on."""
        lib = reader.Library(LESSONS)
        for full, on, off in ((False, "Your path", "Whole library"), (True, "Whole library", "Your path")):
            if lib.full != full:
                lib.key("f")
            tabs = next(t for r, c, t in lib.list_screen(100, 40) if "[f]" in t)
            self.assertIn(render.REV + reader.ACCENT + f" {on} ", tabs)
            self.assertIn(render.DIM + f" {off} ", tabs)
            self.assertIn(reader.ACCENT + render.BOLD + "[f]", tabs)
            keys = " ".join(t for r, c, t in lib.list_screen(100, 40) if "q: quit" in t)
            self.assertNotIn("f:", keys)                         # f lives on the tabs line only

    def test_the_path_skips_mastered_lessons_and_unread_come_first(self):
        with state.locked() as s:
            s["achievements"] = ["exit_code"]
            s["commands"] = 600
            s["lessons"]["read"] = ["command_line", "help"]
        lib = reader.Library(LESSONS)
        ids = [le["id"] for le in lib.lessons]
        self.assertNotIn("command_line", ids)                    # mastered
        open_ = [i for i in ids if lesson.status(lib.s, BY_ID[i]) == "next"]
        self.assertEqual(open_[-1], "help", "read ones after the unread ones")

    def test_a_lesson_off_the_path_opens_the_whole_library(self):
        with state.locked() as s:
            s["lessons"]["opened"] = list(BY_ID)                # all open: the path holds the first ones
        lib = reader.Library(LESSONS, "certs_revoke")
        self.assertTrue(lib.full)
        self.assertEqual(lib.lessons[lib.pos]["id"], "certs_revoke")
        self.assertEqual(lib.lesson["id"], "certs_revoke")

    def test_enter_on_a_locked_lesson_goes_to_the_one_to_practice_in_both_views(self):
        lib = reader.Library(LESSONS)
        lib.key("f")
        lib.pos = next(i for i, le in enumerate(lib.lessons) if le["id"] == "disk")
        lib.key("f")                                             # back to the path, disk isn't on it
        lib.key("f")
        lib.pos = next(i for i, le in enumerate(lib.lessons) if le["id"] == "disk")
        lib.key("enter")
        self.assertEqual(lib.lessons[lib.pos]["id"], "command_line")


class SystemdInLinuxTest(unittest.TestCase):
    def test_no_systemd_skill_or_topic(self):
        self.assertNotIn("systemd", skills.SKILLS)
        self.assertNotIn("systemd", world.TOPICS)

    def test_the_services_lesson_is_linux_for_linux(self):
        le = BY_ID["services"]
        self.assertEqual((le["skill"], le.get("os")), ("linux", "linux"))
        self.assertEqual(reader.group(le), "Linux")

    def test_the_unit_imp_fights_for_linux_on_linux(self):
        ch = challenges.BY_ID["unit_imp"]
        self.assertEqual((ch.skill, ch.os), ("linux", "linux"))

    def test_the_linux_topic_asks_the_systemd_questions_on_linux_only(self):
        ids = {q["id"] for q in quiz.bank("linux")}
        self.assertIn("systemd-1-01", ids)
        self.assertNotIn("systemd-1-01", {q["id"] for q in quiz.for_os(quiz.bank("linux"), {"macos"})})
        self.assertIn("systemd-1-01", {q["id"] for q in quiz.for_os(quiz.bank("linux", "fr"), {"linux"})})

    def test_a_save_that_learned_systemd_learns_linux(self):
        s = state.default()
        s["version"] = 8
        s["skills"] = ["bash", "systemd"]
        s["adventure"] = {"topic": "systemd", "levels": {"systemd": 3, "linux": 2},
                          "bosses": [{"topic": "systemd"}, {"topic": "bash"}]}
        state.migrate(s)
        self.assertEqual(s["skills"], ["bash", "linux"])
        self.assertEqual(s["adventure"]["topic"], "linux")
        self.assertEqual(s["adventure"]["levels"], {"linux": 3})
        self.assertEqual([b["topic"] for b in s["adventure"]["bosses"]], ["linux", "bash"])
        s = state.default()
        s["version"] = 8
        s["skills"] = ["linux", "systemd"]
        state.migrate(s)
        self.assertEqual(s["skills"], ["linux"])


class LessonQuizTest(unittest.TestCase):
    """Owner, 2026-10-27 (option A): every lesson gets its own questions, so it ends on a quiz and right
    answers, at its end or in the adventure, pass it (open what comes next). They never master it."""

    def test_every_lesson_has_its_own_questions(self):
        en = {q["id"] for topic in world.TOPICS for q in quiz.bank(topic, "en")}
        fr = {q["id"] for topic in world.TOPICS for q in quiz.bank(topic, "fr")}
        for le in LESSONS:
            with self.subTest(le["id"]):
                own = le.get("questions", [])
                self.assertGreaterEqual(len(own), 3)
                self.assertLessEqual(set(own), en)
                self.assertLessEqual(set(own), fr)                    # translated too
                self.assertLessEqual(set(le["recall"]), set(own))     # its warm-up questions are its own

    def right(self, s, ids):
        s.setdefault("lessons", {}).setdefault("right", []).extend(ids)

    def test_three_right_answers_pass_a_lesson_not_master_it(self):
        s = state.default()
        grep = BY_ID["grep"]
        self.assertFalse(lesson.passed(s, grep))
        self.right(s, grep["questions"][:2])
        self.assertFalse(lesson.passed(s, grep))
        self.right(s, grep["questions"][2:3])
        self.assertTrue(lesson.passed(s, grep))
        self.assertFalse(lesson.mastered(s, grep))

    def test_on_a_mac_the_questions_you_are_shown_are_enough(self):
        s = state.default()
        s.setdefault("settings", {})["os"] = "macos"
        computer = BY_ID["computer"]
        mine = [q for q in computer["questions"] if not lesson.question_os().get(q)]
        self.assertEqual(lesson.quiz_pass(s, computer), min(3, len(mine)))
        self.right(s, mine[:lesson.quiz_pass(s, computer)])
        self.assertTrue(lesson.passed(s, computer))

    def test_answers_dont_open_a_lesson_that_waits_for_mastery(self):
        s = state.default()
        self.right(s, BY_ID["stack_heap"]["questions"])
        self.assertTrue(lesson.passed(s, BY_ID["stack_heap"]))
        self.assertFalse(lesson.unlocked(s, BY_ID["pointers"]))

    def test_a_lesson_ends_on_its_quiz_and_says_how_many_pass_it(self):
        s = state.default()
        quiz_ = reader.end_quiz(s, BY_ID["grep"])
        self.assertTrue(quiz_)
        text = " ".join(render.strip(t) for r, c, t in reader.warmup_screen(
            BY_ID["grep"], quiz_, len(quiz_), 0, None, 100, 40, final=True, need=lesson.quiz_pass(s, BY_ID["grep"])))
        self.assertIn("3 right answers", text)


class GitAndRustLessonsTest(unittest.TestCase):
    """Owner, 2026-10-27 (option B): the thin sections grow, Git and Rust first."""

    def test_git_is_one_lesson_with_conflicts_stash_and_undo(self):
        """Owner, 2026-10-28: git_fix went back into git, one lesson of 7 pages."""
        git = BY_ID["git"]
        self.assertNotIn("git_fix", BY_ID)
        self.assertEqual(reader.section(git), "git")
        self.assertEqual(len(git["pages"]), 7)
        self.assertLessEqual({"commit_crowd", "branch_bramble", "conflict_chimera", "revert_revenant"}, set(git["fights"]))
        self.assertIn("stasher", " ".join(git["masters"]))

    def test_rust_has_a_lesson_on_ownership_and_borrowing(self):
        own = BY_ID["rust_own"]
        self.assertEqual((own["skill"], own["after"], own.get("opens")), ("rust", ["rust_vars"], "mastered"))
        self.assertEqual(set(own["fights"]), {"borrow_badger", "vector_viper"})
        self.assertEqual(reader.group(own), "Rust")

    def test_the_new_fights_exist_with_their_sprites(self):
        for fid in ("revert_revenant", "borrow_badger", "vector_viper"):
            with self.subTest(fid):
                self.assertIn(fid, challenges.BY_ID)
                self.assertTrue((Path(lesson.HERE).parent / "enemies" / f"{fid}.json").exists())


class PythonAndSqlLessonsTest(unittest.TestCase):
    """Option B, next thin sections: Python errors and exit codes, SQL's NULL."""

    def test_python_has_a_lesson_on_errors_and_exit_codes(self):
        le = BY_ID["py_errors"]
        self.assertEqual((le["skill"], le["after"], le["fights"]), ("python", ["py_flow"], ["except_eel"]))

    def test_sql_has_a_lesson_on_null(self):
        le = BY_ID["sql_null"]
        self.assertEqual((le["skill"], le["after"], le["fights"]), ("sql", ["sql_write"], ["null_newt"]))
        self.assertTrue(any(p.get("sql") for p in le["pages"]))             # its statements run in the tests

    def test_the_new_fights_exist_with_their_sprites(self):
        for fid in ("except_eel", "null_newt"):
            with self.subTest(fid):
                self.assertIn(fid, challenges.BY_ID)
                self.assertTrue((Path(lesson.HERE).parent / "enemies" / f"{fid}.json").exists())
