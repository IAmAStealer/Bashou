"""What you want to learn: fights, adventure paths and the Rust invitation follow your skills."""

import random
import unittest
from unittest import mock

from bashou import challenges, dialogue, fight, skills, state
from bashou.adventure import world


class SkillsTest(unittest.TestCase):
    def test_every_fight_has_a_known_skill(self):
        for ch in challenges.ALL:
            self.assertIn(ch.skill, skills.SKILLS, ch.id)

    def test_the_programs_a_skill_shows_are_the_ones_its_fights_need(self):
        """Owner: the skills picker shows the extra programs and why. Each one shown must really be needed
        by a fight of that skill (or be marked optional), and Bashou must know how to install it."""
        from bashou import which
        for key, skill in skills.SKILLS.items():
            needed = {t for c in challenges.ALL if c.skill == key for t in (c.requires or [c.tool])}
            for program, why in skill.uses:
                with self.subTest(skill=key, program=program):
                    self.assertTrue(program in needed or program in skills.OPTIONAL)
                    self.assertIn(program, which.PACKAGES)
                    self.assertTrue(why)
            if skill.needs:
                self.assertIn(skill.needs, [p for p, _w in skill.uses], key)

    def test_the_picker_says_what_is_missing_and_how_to_get_it(self):
        from bashou import starter
        with mock.patch("bashou.which.installed", lambda program: program != "gdb"), \
                mock.patch("bashou.which.os_family", return_value=frozenset({"debian"})):
            text = "\n".join(starter.uses_lines("c", 100))
            self.assertIn("gcc: builds the C programs", text)
            self.assertIn("✗", text)
            self.assertIn("sudo apt install gdb", text)
            self.assertIn("its fights wait", text)
            self.assertEqual(skills.missing(list(skills.SKILLS)), ["gdb"])
            self.assertIn("gdb", "".join(starter.missing_note(list(skills.SKILLS), 100)))
        with mock.patch("bashou.which.installed", lambda program: program != "yamllint"):
            self.assertNotIn("its fights wait", "\n".join(starter.uses_lines("cicd", 100)))   # optional
        self.assertIn("Nothing to install", "\n".join(starter.uses_lines("logic", 100)))

    def test_skills_are_the_adventure_topics(self):
        self.assertEqual(set(skills.SKILLS), set(world.TOPICS))

    def test_only_fights_of_your_skills(self):
        s = state.default()
        everything = {c.skill for c in fight.remaining(s)}
        s["skills"] = ["python"]
        mine = fight.remaining(s)
        self.assertTrue(all(c.skill == "python" for c in mine))
        if "python" in everything:
            self.assertTrue(mine)

    def test_forks_offer_your_topics_first(self):
        for chapter, leg in ((1, 0), (2, 1), (3, 2)):
            adv = {"chapter": chapter, "leg": leg}
            self.assertEqual(set(world.fork_options(adv, ["python", "c", "rust"])) & {"python", "c", "rust"},
                             set(world.fork_options(adv, ["python", "c", "rust"])))
            options = world.fork_options(adv, ["logic"])            # one topic: others fill the fork
            self.assertIn("logic", options)
            self.assertEqual(len(set(options)), 2 if chapter == 1 else 3)
            self.assertEqual(options, world.fork_options(adv, ["logic"]))   # same fork, same choice

    def test_rust_learners_are_invited_right_away(self):
        s = state.default()
        s.update(adventure={"chapter": 1}, security=[1])
        with mock.patch("bashou.which.installed", return_value=False):
            self.assertIsNone(dialogue.invite(s, random.Random(1)))           # all skills: 15 achievements first
            s["skills"] = ["rust"]
            self.assertIn("Rust", dialogue.invite(s, random.Random(1)))
            s["skills"] = ["python"]
            s["achievements"] = ["x"] * 20
            self.assertIsNone(dialogue.invite(s, random.Random(1)))           # not what you want to learn


if __name__ == "__main__":
    unittest.main()
