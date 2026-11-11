"""Owner, 2026-11-11: whatever a player ticks at the start, every lesson and fight of those skills must be
reachable. A player is simulated: they read every lesson that is open, answer its questions right, try the
commands the pets name and win every fight that comes, until nothing new opens. What is left locked is a dead end."""

import unittest
from unittest import mock

from bashou import challenges, fight, lesson, skills, state

LESSONS = lesson.load("en")


def play(picked, os_="linux"):
    """The save of a player who ticked `picked` (a list, or "all") and did everything that came."""
    s = state.default()
    s["skills"] = picked
    s.setdefault("settings", {})["os"] = os_
    systems = skills.oses(s)
    while True:
        before = (len(lesson.read(s)), len(lesson.right(s)), len(s["challenges"]))
        for le in lesson.shown(s, LESSONS):
            if lesson.unlocked(s, le):
                if le["id"] not in s["lessons"]["read"]:
                    s["lessons"]["read"].append(le["id"])
                for q in le.get("questions", []):
                    if skills.shows({"os": lesson.question_os().get(q)}, systems):
                        lesson.record_right(s, q)
        for tool in fight.to_discover(s):                    # the pets name them: the player tries them
            if tool == "|":
                s["constructs"]["pipe3"] = 1
            else:
                s["tools"][tool] = 1
        for ch in fight.remaining(s):
            if fight.ready(s, ch):
                s["challenges"].append(ch.id)
        if (len(lesson.read(s)), len(lesson.right(s)), len(s["challenges"])) == before:
            return s


def fights_of(s):
    """The fights this player should meet: their skills, their systems."""
    return [c for c in challenges.ALL if skills.wanted(s, c.skill) and c.available()]


def lessons_of(s):
    return [le for le in lesson.shown(s, LESSONS)]


class ReachableTest(unittest.TestCase):
    def setUp(self):
        # Every program is installed and every fight can run: reachability is about the game's paths only.
        patch = mock.patch.object(challenges.Challenge, "available", lambda self: True)
        patch.start()
        self.addCleanup(patch.stop)
        if hasattr(lesson.question_os, "cache_clear"):
            self.addCleanup(lesson.question_os.cache_clear)

    def check(self, picked, os_="linux"):
        s = play(picked, os_)
        locked = [le["id"] for le in lessons_of(s) if not lesson.unlocked(s, le)]
        unseen = [c.id for c in fights_of(s) if c.id not in s["challenges"]
                  and skills.shows({"os": c.os}, {os_} if c.os else skills.oses(s))]
        self.assertEqual(locked, [], f"lessons out of reach with {picked} on {os_}")
        self.assertEqual(unseen, [], f"fights out of reach with {picked} on {os_}")
        return s

    def test_every_skill_alone(self):
        for os_ in ("linux", "macos", "both"):
            for k in skills.SKILLS:
                with self.subTest(skill=k, os=os_):
                    self.check([k], os_)

    def test_every_pair_of_skills(self):
        keys = list(skills.SKILLS)
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                with self.subTest(skills=(a, b)):
                    self.check([a, b])

    def test_everything(self):
        for os_ in ("linux", "macos", "both"):
            with self.subTest(os=os_):
                self.check("all", os_)

    def test_a_dead_end_is_caught(self):
        """The check itself: a Python fight that waits for a C fight never comes to a Python-only player."""
        py = next(c for c in challenges.ALL if c.skill == "python")
        c_fight = next(c for c in challenges.ALL if c.skill == "c")
        with mock.patch.object(py, "after", (c_fight.id,)):
            with self.assertRaises(AssertionError):
                self.check(["python"])
        shown = {le["id"]: le for le in LESSONS}               # a lesson that waits for a mastery no one can get
        with mock.patch.dict(shown["ai_plan"], opens="mastered"), \
                mock.patch.dict(lesson.by_id()["ai_context"], masters=["achievement no_such_thing"]):
            with self.assertRaises(AssertionError):
                self.check(["ai"])

    def test_a_skill_alone_shows_its_lessons(self):
        """Ticking a skill must give it at least one lesson of its own, beyond the common ones."""
        for k in skills.SKILLS:
            with self.subTest(skill=k):
                s = state.default()
                s["skills"] = [k]
                s.setdefault("settings", {})["os"] = "both"
                self.assertTrue([le for le in lessons_of(s) if k in lesson.skills_of(le)])


if __name__ == "__main__":
    unittest.main()
