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
        with mock.patch("shutil.which", return_value=None):
            self.assertIsNone(dialogue.invite(s, random.Random(1)))           # all skills: 15 achievements first
            s["skills"] = ["rust"]
            self.assertIn("Rust", dialogue.invite(s, random.Random(1)))
            s["skills"] = ["python"]
            s["achievements"] = ["x"] * 20
            self.assertIsNone(dialogue.invite(s, random.Random(1)))           # not what you want to learn


if __name__ == "__main__":
    unittest.main()
