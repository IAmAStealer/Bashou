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

    def test_every_command_achievement_has_an_example(self):
        # Night owl is about the time, not a command.
        missing = [a.id for a in achievements.ALL if a.cmd and a.id not in dialogue.EXAMPLES and a.id != "night_owl"]
        self.assertEqual(missing, [])

    def test_examples_earn_their_achievement(self):
        from bashou import progress
        for a in achievements.ALL:
            if a.cmd and a.id in dialogue.EXAMPLES:
                s = state.default()
                progress.record(s, 0, dialogue.EXAMPLES[a.id], "2026-09-21", 3 if a.id == "night_owl" else 14)
                self.assertIn(a.id, s["achievements"], dialogue.EXAMPLES[a.id])

    def test_typo_suggests_the_closest_command(self):
        s = state.default()
        for typed, fix in (("gerp foo file", "grep"), ("sl -la", "ls"), ("pyhton3 x.py", "python3")):
            text = dialogue.typo(s, "cat", typed, random.Random(0))
            self.assertIn(f"`{fix}`", text, typed)
            self.assertIn(f"`{typed.split()[0]}`", text)
        text = dialogue.typo(s, "fox", "zzqxv", random.Random(0))
        self.assertIn("`zzqxv`", text)
        self.assertTrue(text.startswith("*sniff*"))

    def test_typo_learns_your_tools(self):
        s = state.default()
        s["tools"] = {"kubectl": 30}
        self.assertIn("`kubectl`", dialogue.typo(s, "cat", "kubctl get pods", random.Random(0)))

    def test_no_typo_joke_for_real_commands(self):
        self.assertIsNone(dialogue.typo(state.default(), "cat", "ls /nope", random.Random(0)))

    def test_examples_match_real_achievements(self):
        self.assertLessEqual(set(dialogue.EXAMPLES), set(achievements.BY_ID))
        self.assertLessEqual(set(dialogue.TRAITS), set(achievements.BY_ID))


if __name__ == "__main__":
    unittest.main()
