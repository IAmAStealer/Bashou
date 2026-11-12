"""Owner, 2026-11-11 (TODO "Fights must follow both themes of a shared lesson"): a lesson can belong to several
skills (processes: Linux and Bash). Whatever a player ticks, every fight a lesson they see names (in its
`fights`, or as "won ID" in its `masters`) must be one they can meet and win; otherwise the lesson can't be
mastered, or points to a fight that never comes."""

import unittest
from unittest import mock

from bashou import challenges, lesson, skills

from tests.test_reachable import LESSONS, lessons_of, play

BY_ID = {c.id: c for c in challenges.ALL}


def named_fights(le):
    """The fights a lesson names: its `fights`, and every "won ID" of its `masters`."""
    ids = list(le.get("fights", []))
    for cond in le.get("masters", []):
        for side in cond.split("|"):
            words = side.split()
            if words and words[0] == "won" and words[1] not in ids:
                ids.append(words[1])
    return ids


class FightThemesTest(unittest.TestCase):
    def setUp(self):
        # Every program is installed and every fight can run: this is about the game's paths only.
        patch = mock.patch.object(challenges.Challenge, "available", lambda self: True)
        patch.start()
        self.addCleanup(patch.stop)
        if hasattr(lesson.question_os, "cache_clear"):
            self.addCleanup(lesson.question_os.cache_clear)

    def out_of_reach(self, picked, os_="linux"):
        """(lesson, line) for each `masters` line of a shown lesson that counts for this player but that only
        fights they never win can fill: the lesson could never be mastered."""
        s = play(picked, os_)
        bad = []
        for le in lessons_of(s):
            for fid in le.get("fights", []):
                if fid not in BY_ID:
                    bad.append((le["id"], fid))
            for cond in lesson.needed(s, le):
                sides = [c.split() for c in cond.split("|")]
                if all(w[0] == "won" for w in sides) and not any(w[1] in s["challenges"] for w in sides):
                    bad.append((le["id"], cond))
        return bad

    def test_every_skill_alone(self):
        for k in skills.SKILLS:
            with self.subTest(skill=k):
                self.assertEqual(self.out_of_reach([k]), [], f"fights out of reach with {[k]}")

    def test_every_pair_of_skills(self):
        keys = list(skills.SKILLS)
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                with self.subTest(skills=(a, b)):
                    self.assertEqual(self.out_of_reach([a, b]), [], f"fights out of reach with {[a, b]}")

    def test_a_missing_theme_is_caught(self):
        """The check itself: if a Linux-only player had to win a Bash fight to master processes, it's caught."""
        bash_fight = next(c.id for c in challenges.ALL if c.skill == "bash")
        real = lesson.needed
        with mock.patch.object(lesson, "needed", lambda s, le: [f"won {bash_fight}"] if le["id"] == "processes"
                               else real(s, le)):
            self.assertIn(("processes", f"won {bash_fight}"), self.out_of_reach(["linux"]))

    def test_a_line_of_unticked_fights_is_skipped(self):
        """Regression: Linux-only players could never master processes (won ps_phantom, a Bash fight)."""
        s = play(["linux"], "linux")
        processes = lesson.by_id()["processes"]
        self.assertNotIn("won ps_phantom", lesson.needed(s, processes))
        self.assertIn("won ps_phantom", lesson.needed({**s, "skills": "all"}, processes))

    def test_a_lesson_with_only_unticked_fights_counts_as_mastered(self):
        """Regression: a Rust-only player could never master bash_zsh (its one line is index_imp, a Bash fight)."""
        s = {"skills": ["rust"], "challenges": [], "achievements": []}
        bash_zsh = lesson.by_id()["bash_zsh"]
        self.assertEqual(lesson.needed(s, bash_zsh), [])
        self.assertTrue(lesson.mastered(s, bash_zsh))
        self.assertFalse(lesson.mastered({**s, "skills": "all"}, bash_zsh))

    def test_an_unticked_lesson_passes_its_wait_on(self):
        """Regression: a Bash-only player saw substitution and loops open at once, before command_line: they wait
        for scripts (Script skill), and an unticked lesson didn't count. It now hands over its own `after` (quotes)."""
        s = {"skills": ["bash"], "challenges": [], "achievements": [], "lessons": {}}
        by_id = lesson.by_id()
        for lid in ("substitution", "loops"):
            with self.subTest(lesson=lid):
                self.assertIn("quotes", [le["id"] for le in lesson.waiting_for(s, by_id[lid])])
                self.assertFalse(lesson.unlocked(s, by_id[lid]))
                self.assertIn("scripts", [le["id"] for le in lesson.waiting_for({**s, "skills": "all"}, by_id[lid])])


if __name__ == "__main__":
    unittest.main()
