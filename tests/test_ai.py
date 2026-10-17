"""The AI tools skill (owner, 2026-10-16): lessons on context, memory and planning, adventure questions,
no fights. A lesson of this skill passes with right answers to its own questions ("answered ID N"),
given in the adventure or in the quiz at the end of the lesson."""

import random
import tempfile
import unittest
from pathlib import Path

from bashou import lesson, skills, state, transfer
from bashou.adventure import quiz, sprites, world
from bashou.lesson import reader

LESSONS = lesson.load("en")
BY_ID = {le["id"]: le for le in LESSONS}
AI = ("ai_context", "ai_plan")


class Saved(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = state.DATA, state.STATE
        state.DATA = Path(self.tmp.name)
        state.STATE = state.DATA / "state.json"

    def tearDown(self):
        state.DATA, state.STATE = self.saved
        self.tmp.cleanup()


class SkillTest(unittest.TestCase):
    def test_the_skill_is_offered_everywhere(self):
        self.assertIn("ai", skills.SKILLS)
        self.assertFalse(skills.SKILLS["ai"].needs)
        self.assertFalse(skills.SKILLS["ai"].os)
        for os_ in ("linux", "macos"):
            self.assertIn("ai", skills.topics({"settings": {"os": os_}}))

    def test_the_adventure_has_its_path_and_boss(self):
        self.assertIn("ai", world.TOPICS)
        self.assertIn("ai", sprites.BOSSES)
        rows, palette = sprites.boss("ai")
        self.assertEqual({len(r) for r in rows}, {19})
        self.assertTrue(set("".join(rows)) - {"."} <= set(palette))


class QuestionsTest(unittest.TestCase):
    def test_the_banks(self):
        en, fr = quiz.bank("ai", "en"), quiz.bank("ai", "fr")
        self.assertEqual(quiz.problems(en), [])
        self.assertEqual(quiz.problems(fr), [])
        self.assertEqual([(q["id"], q["level"], q["answer"]) for q in fr],
                         [(q["id"], q["level"], q["answer"]) for q in en])
        self.assertEqual(sorted({q["level"] for q in en}), [1, 2, 3])

    def test_each_lesson_has_its_own_questions(self):
        ids = {q["id"] for q in quiz.bank("ai", "en")}
        mine = []
        for lid in AI:
            le = BY_ID[lid]
            self.assertGreaterEqual(len(le["questions"]), 4, lid)
            self.assertLessEqual(set(le["questions"]), ids, lid)
            mine += le["questions"]
        self.assertEqual(len(mine), len(set(mine)))                 # a question belongs to one lesson


class LessonsTest(unittest.TestCase):
    def test_two_lessons_no_fights(self):
        fr = {le["id"]: le for le in lesson.load("fr")}
        for lid in AI:
            le = BY_ID[lid]
            self.assertEqual(le["skill"], "ai")
            self.assertFalse(le.get("fights"))
            self.assertEqual(le["masters"], [f"answered {lid} 3"])
            self.assertEqual(len(fr[lid]["pages"]), len(le["pages"]))
            self.assertNotEqual(fr[lid]["title"], le["title"])
        self.assertIn("ai_context", BY_ID["ai_plan"]["after"])

    def test_vendor_neutral_facts(self):
        text = " ".join(" ".join(p.get("text", []) + p.get("scheme", [])) for p in BY_ID["ai_context"]["pages"])
        for word in ("context", "token", "CLAUDE.md", "AGENTS.md", "secret"):
            self.assertIn(word, text)
        text = " ".join(" ".join(p.get("text", []) + p.get("scheme", [])) for p in BY_ID["ai_plan"]["pages"])
        for word in ("plan", "diff", "test"):
            self.assertIn(word, text)


class AnsweredTest(unittest.TestCase):
    def save(self, right):
        s = state.default()
        s["lessons"]["right"] = list(right)
        return s

    def test_answered_counts_the_lesson_questions_only(self):
        qs = BY_ID["ai_context"]["questions"]
        other = BY_ID["ai_plan"]["questions"]
        self.assertFalse(lesson.met(self.save(qs[:2] + other), "answered ai_context 3"))
        self.assertTrue(lesson.met(self.save(qs[:3]), "answered ai_context 3"))

    def test_right_answers_pass_and_master_the_lesson(self):
        le = BY_ID["ai_context"]
        self.assertFalse(lesson.passed(self.save([]), le))
        s = self.save(le["questions"][:3])
        self.assertTrue(lesson.passed(s, le))
        self.assertTrue(lesson.mastered(s, le))
        s["skills"] = ["ai"]
        self.assertTrue(lesson.unlocked(s, BY_ID["ai_plan"]))

    def test_the_condition_in_words(self):
        s = self.save(BY_ID["ai_context"]["questions"][:1])
        self.assertEqual(reader.describe("answered ai_context 3", s), "answer 3 of its questions right (1/3)")
        self.assertIn("answer 3 of its questions right (1/3)", reader.ways_to_pass(s, BY_ID["ai_context"]))

    def test_old_saves_have_no_right_answers(self):
        s = state.read('{"version": 6, "lessons": {"read": ["command_line"]}}')
        self.assertEqual(s["lessons"]["right"], [])
        self.assertEqual(state.SAVE_VERSION, 6)                       # a new list with a default: no migration


class AdventureTest(Saved):
    def test_a_right_answer_is_remembered(self):
        from bashou.adventure import game as adventure
        with state.locked() as s:
            s["starter"] = "pebble"
        g = adventure.Game(80, 24, rng=random.Random(0))
        g.adv.update(topic="ai", phase="monster")
        g.question = g.ask()
        qid = g.question["id"]
        g.answer((g.question["answer"] + 1) % 4, 0)
        self.assertNotIn(qid, lesson.right(state.load()))
        g.adv["phase"] = "monster"
        g.question = {**quiz.bank("ai")[0], "answer": 0}
        g.answer(0, 0)
        g.question = {**quiz.bank("ai")[0], "answer": 0}
        g.answer(0, 0)
        self.assertEqual(lesson.right(state.load()), [quiz.bank("ai")[0]["id"]])


class EndQuizTest(Saved):
    def open(self, lid):
        with state.locked() as s:
            s["skills"] = ["ai"]
            s["lessons"]["opened"] = list(AI)
        lib = reader.Library(LESSONS, lid)
        lib.quiz = []                                                    # no warm-up
        return lib

    def read_to_the_end(self, lib):
        for _ in lib.lesson["pages"]:
            lib.key("enter")

    def test_the_quiz_after_the_last_page_passes_the_lesson(self):
        lib = self.open("ai_context")
        self.read_to_the_end(lib)
        self.assertIsNotNone(lib.lesson)                                 # the quiz, before the list
        self.assertEqual(len(lib.quiz), reader.END_QUIZ)
        self.assertLessEqual({q["id"] for q in lib.quiz}, set(BY_ID["ai_context"]["questions"]))
        screen = " ".join(t for _r, _c, t in lib.screen(80, 24))
        self.assertIn("Quiz", screen)
        while lib.quiz:
            lib.choice = lib.quiz[0]["answer"]
            lib.key("enter")                                             # answer
            lib.key("enter")                                             # next question
        self.assertIsNone(lib.lesson)
        s = state.load()
        self.assertIn("ai_context", s["lessons"]["read"])
        self.assertTrue(lesson.passed(s, BY_ID["ai_context"]))
        self.assertIn("Lesson done", lib.message)

    def test_wrong_answers_dont_count_and_q_skips(self):
        lib = self.open("ai_context")
        self.read_to_the_end(lib)
        q = lib.quiz[0]
        lib.choice = (q["answer"] + 1) % 4
        lib.key("enter")
        self.assertNotIn(q["id"], lesson.right(state.load()))
        lib.key("quit")
        self.assertIsNone(lib.lesson)
        self.assertIn("ai_context", state.load()["lessons"]["read"])

    def test_the_quiz_asks_what_isnt_answered_yet(self):
        with state.locked() as s:
            s["lessons"]["right"] = BY_ID["ai_context"]["questions"][:-1]
        lib = self.open("ai_context")
        self.read_to_the_end(lib)
        self.assertEqual([q["id"] for q in lib.quiz], BY_ID["ai_context"]["questions"][-1:])

    def test_a_lesson_without_questions_has_no_quiz(self):
        lib = reader.Library(LESSONS, "command_line")
        lib.quiz = []
        self.read_to_the_end(lib)
        self.assertIsNone(lib.lesson)


class TransferTest(unittest.TestCase):
    def test_right_answers_travel_in_the_minimal_save(self):
        s = state.default()
        s["lessons"]["right"] = ["ai-1-01", "ai-1-02"]
        data = transfer.payload(s, "minimal")
        self.assertEqual(data["lessons"]["right"], ["ai-1-01", "ai-1-02"])
        self.assertNotIn("right", data["adventure"])
        mode, back = transfer.decode(transfer.encode(s))
        merged = transfer.merge(state.default(), back, mode)
        self.assertEqual(merged["lessons"]["right"], ["ai-1-01", "ai-1-02"])


if __name__ == "__main__":
    unittest.main()
