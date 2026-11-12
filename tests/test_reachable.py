"""Owner, 2026-11-11: whatever a player ticks at the start, every lesson and fight of those skills must be
reachable. A player is simulated: they read every lesson that is open, answer its questions right, try the
commands the pets name and win every fight that comes, until nothing new opens. What is left locked is a dead end."""

import unittest
from unittest import mock

from bashou import challenges, fight, lesson, skills, state, which

LESSONS = lesson.load("en")


def play(picked, os_="linux", opened=None, fights=True):
    """The save of a player who ticked `picked` (a list, or "all") and did everything that came. `picked` None:
    the base config, a fresh save untouched (every skill, the system Bashou runs on). `opened`: a list that gets
    (lesson id, fights won before, pass, lessons passed by then) for each lesson as it opens. Each pass takes the open lessons first, then
    reads them: lessons that open together share a pass, so one can't hide that it opened with its prerequisite.
    `fights` False: a player who only does lessons (fights won early open lessons early, on purpose)."""
    s = state.default()
    if picked is not None:
        s["skills"] = picked
        s.setdefault("settings", {})["os"] = os_
    systems = skills.oses(s)
    turn = 0
    while True:
        turn += 1
        before = (len(lesson.read(s)), len(lesson.right(s)), len(s["challenges"]))
        done = {le["id"] for le in LESSONS if lesson.passed(s, le)}   # passed by doing, even while still locked
        for le in [le for le in lesson.shown(s, LESSONS) if lesson.unlocked(s, le)]:
            if le["id"] not in s["lessons"]["read"]:
                s["lessons"]["read"].append(le["id"])
                if opened is not None:
                    opened.append((le["id"], set(s["challenges"]), turn, done))
            for q in le.get("questions", []):
                if skills.shows({"os": lesson.question_os().get(q)}, systems):
                    lesson.record_right(s, q)
        for tool in fight.to_discover(s):                    # the pets name them: the player tries them
            if tool == "|":
                s["constructs"]["pipe3"] = 1
            else:
                s["tools"][tool] = 1
        for ch in fight.remaining(s) if fights else []:
            if fight.ready(s, ch):
                s["challenges"].append(ch.id)
        if (len(lesson.read(s)), len(lesson.right(s)), len(s["challenges"])) == before:
            return s


# Typical ticks at the start (owner, 2026-11-12: "several tests depending on what is ticked").
PROFILES = {
    "beginner": ["logic", "fundamentals", "bash"],
    "sysadmin_debian": ["bash", "script", "linux", "debian", "network"],
    "sysadmin_rocky": ["bash", "script", "linux", "rocky", "network"],
    "devops": ["bash", "script", "linux", "cicd", "network", "python"],
    "python_dev": ["python", "sql", "logic"],
    "systems_dev": ["c", "rust", "linux"],
    "data": ["sql", "python", "bash"],
    "ai_user": ["ai", "fundamentals", "python"],
    "everything_but_bash": [k for k in skills.SKILLS if k not in ("bash", "script")],
}


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
        os_ = os_ if picked is not None else which.platform()
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

    def test_base_config(self):
        """Owner, 2026-11-12: a fresh save left as it is (every skill, the system Bashou runs on) starts at the
        command line alone, and everything opens from there."""
        for os_ in ("linux", "macos"):
            with self.subTest(os=os_), mock.patch.object(which, "platform", lambda os_=os_: os_):
                s = state.default()
                self.assertEqual([le["id"] for le in lessons_of(s) if lesson.unlocked(s, le)], ["command_line"])
                self.check(None, os_)

    def test_base_config_opens_in_order(self):
        """With the base config, a player who only does lessons never sees one open before the lessons it waits
        for (its `after`, or what an unticked one waits for in its place)."""
        for os_ in ("linux", "macos"):
            with self.subTest(os=os_), mock.patch.object(which, "platform", lambda os_=os_: os_):
                opened = []
                s = play(None, opened=opened, fights=False)
                self.assertEqual(self.out_of_order(s, opened), [])

    def test_every_skill_alone_opens_in_order(self):
        for k in skills.SKILLS:
            with self.subTest(skill=k):
                opened = []
                s = play([k], "both", opened, fights=False)
                self.assertEqual(self.out_of_order(s, opened), [])

    def test_every_pair_of_skills_opens_in_order(self):
        keys = list(skills.SKILLS)
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                with self.subTest(skills=(a, b)):
                    opened = []
                    s = play([a, b], "both", opened, fights=False)
                    self.assertEqual(self.out_of_order(s, opened), [])

    def test_typical_players(self):
        """Ticks a real player makes: reachable and in order, on each system."""
        for name, picked in PROFILES.items():
            for os_ in ("linux", "macos", "both"):
                with self.subTest(profile=name, os=os_):
                    opened = []
                    self.check(picked, os_)
                    s = play(picked, os_, opened, fights=False)
                    self.assertEqual(self.out_of_order(s, opened), [])

    def test_everything_opens_in_order(self):
        for os_ in ("linux", "macos", "both"):
            with self.subTest(os=os_):
                opened = []
                s = play("all", os_, opened, fights=False)
                self.assertEqual(self.out_of_order(s, opened), [])

    def out_of_order(self, s, opened):
        """(lesson, prerequisite) for each lesson that opened before one of its prerequisites (or in the same pass),
        that prerequisite not passed by doing either."""
        by_id, when, bad = lesson.by_id(), {}, []

        def before(lid, done=()):
            for p in by_id[lid].get("after", []):
                ks = lesson.skills_of(by_id[p])
                if ks and not any(skills.wanted(s, k) for k in ks):
                    yield from before(p, done + (lid,)) if p not in done else ()
                else:
                    yield p
        for lid, won, turn, done in opened:
            when[lid] = turn
        for lid, won, turn, done in opened:
            if not won & set(by_id[lid].get("fights", [])):
                bad += [(lid, p) for p in before(lid) if when.get(p, turn) >= turn and p not in done]
        return bad

    def test_out_of_order_is_caught(self):
        """The check itself: a lesson opened before what it waits for is reported."""
        s = state.default()
        self.assertIn(("loops", "scripts"), self.out_of_order(s, [("loops", set(), 1, set()), ("scripts", set(), 2, set())]))
        bash = {**s, "skills": ["bash"]}                         # scripts unticked: loops waits for quotes instead
        self.assertNotIn(("loops", "quotes"), self.out_of_order(bash, [("quotes", set(), 1, set()), ("loops", set(), 2, set())]))
        self.assertIn(("loops", "quotes"), self.out_of_order(bash, [("quotes", set(), 1, set()), ("loops", set(), 1, set())]))
        won = {"rename_rat"}                                     # a fight of its own came first: it may open early
        self.assertNotIn(("loops", "scripts"), self.out_of_order(s, [("loops", won, 1, set())]))
        self.assertNotIn(("loops", "scripts"), self.out_of_order(s, [("loops", set(), 1, {"scripts"})]))  # passed by doing

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
