"""Logic fight and chest tasks say what's wrong, the goal and how to test, each on its own line (a player found
them hard to follow, 2026-11-12)."""

import json
import unittest
from pathlib import Path

from bashou.challenges import logic

FR = json.loads((Path(__file__).resolve().parent.parent / "bashou/locales/fr.json").read_text())


class LogicTasks(unittest.TestCase):
    def test_goal_on_its_own_line(self):
        for ch in logic.ALL + logic.CHESTS:
            with self.subTest(ch.id):
                lines = ch.task.split("\n")
                self.assertGreaterEqual(len(lines), 3)
                self.assertTrue(any(line.startswith("Goal: ") for line in lines))
                self.assertIn("verify", ch.task)
                fr = FR[ch.task].split("\n")
                self.assertEqual(len(fr), len(lines))
                self.assertTrue(any(line.startswith("But : ") for line in fr))

    def test_says_what_it_prints(self):
        """The goal names the words the script must print, not a vague "fix it"."""
        words = {"negation_gnome": ("open", "closed"), "coin_wraith": ("saved", "missing"),
                 "trial_logic_door": ("open", "closed"), "trial_logic_parity": ("flipped", "ok")}
        for ch in logic.ALL + logic.CHESTS:
            for word in words.get(ch.id, ()):
                with self.subTest(ch.id, word=word):
                    self.assertRegex(ch.task, rf"\b{word}\b")


if __name__ == "__main__":
    unittest.main()
