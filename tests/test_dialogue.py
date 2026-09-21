import random
import unittest

from bashou import achievements, dialogue, render, state
from bashou.creatures import ROSTER


class DialogueTest(unittest.TestCase):
    def test_every_pet_has_a_voice_and_tips(self):
        for pet, _ in ROSTER:
            self.assertIn(pet, dialogue.VOICE)
            self.assertGreaterEqual(len(dialogue.TIPS[pet]), 3)
            self.assertIn(pet, dialogue.PERSONAL)

    def test_lines_fit_a_bubble(self):
        s = state.default()
        rng = random.Random(0)
        for pet, _ in ROSTER:
            for _ in range(50):
                text = dialogue.line(s, pet, rng)
                self.assertLessEqual(render.width(text), 90, text)
                self.assertNotIn("\n", text)

    def test_hint_points_to_the_family_first(self):
        s = state.default()
        text = dialogue.hint(s, "fox", random.Random(1))
        fox = [a.name for a in achievements.family("fox") if not a.state]
        self.assertTrue(any(f"({name})" in text for name in fox), text)
        s["achievements"] = [a.id for a in achievements.family("fox")]
        text = dialogue.hint(s, "fox", random.Random(1))
        self.assertFalse(any(f"({name})" in text for name in fox), text)

    def test_traits_come_from_achievements(self):
        s = state.default()
        s["achievements"] = ["warrior"]
        said = {dialogue.line(s, "cat", random.Random(i)) for i in range(300)}
        self.assertTrue(any("claws" in t or "threats around" in t for t in said))
        self.assertFalse(any("Late again" in t or "nicer at night" in t for t in said))

    def test_examples_match_real_achievements(self):
        self.assertLessEqual(set(dialogue.EXAMPLES), set(achievements.BY_ID))
        self.assertLessEqual(set(dialogue.TRAITS), set(achievements.BY_ID))


if __name__ == "__main__":
    unittest.main()
