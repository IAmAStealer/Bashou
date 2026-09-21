import unittest

from bashou import progress, state


class ProgressTest(unittest.TestCase):
    def setUp(self):
        self.s = state.default()

    def run_cmd(self, line, status=0, times=1, hour=14):
        notes = []
        for _ in range(times):
            notes += progress.record(self.s, status, line, "2026-09-21", hour)
        return notes

    def test_command_milestone(self):
        self.assertEqual(self.run_cmd("ls", times=49), [])
        notes = self.run_cmd("ls")
        self.assertIn("frog", self.s["pets"])
        self.assertEqual(len(notes), 1)
        self.assertIn("Tadpole", notes[0])

    def test_tool_pet_needs_successes(self):
        self.run_cmd("find . -name x", status=1, times=20)
        self.assertNotIn("fox", self.s["pets"])
        self.run_cmd("sudo find . -name x", times=10)
        self.assertIn("fox", self.s["pets"])
        self.assertEqual(self.s["tools"]["find"], 10)

    def test_unlock_once(self):
        self.run_cmd("strace ls", times=3)
        self.assertEqual(self.s["pets"].count("spider"), 1)
        self.assertEqual(self.run_cmd("strace ls"), [])

    def test_constructs(self):
        self.run_cmd("cat f | sort | uniq -c | head")
        self.assertEqual(self.s["constructs"]["pipe3"], 1)
        self.assertEqual(self.s["days"], ["2026-09-21"])


    def test_achievement_and_evolution(self):
        self.run_cmd("find . -mtime -1", times=10)
        self.assertIn("time_traveller", self.s["achievements"])
        self.assertEqual(progress.stage(self.s, "fox"), 1)
        notes = self.run_cmd("find . -name '*.log' -exec rm {} +")
        self.assertIn("🏆 Executor: act on results with `find -exec`", notes)
        self.assertIn("✨ Fox cub evolved into Fox! New: wash, hum, flick its tail", notes)
        self.assertEqual(progress.stage(self.s, "fox"), 2)

    def test_failed_commands_earn_nothing(self):
        self.run_cmd("grep -r foo .", status=2)
        self.assertNotIn("digger", self.s["achievements"])

    def test_command_rules(self):
        self.run_cmd("cat access.log | awk -F' ' '{ s += $10 } END { print s }'")
        self.run_cmd("ls", hour=3)
        self.run_cmd("echo $(basename $(pwd))")
        self.run_cmd('while IFS= read -r l; do echo "$l"; done < f')
        for a in ("field_reader", "accountant", "night_owl", "nested", "capture", "reader"):
            self.assertIn(a, self.s["achievements"])
        self.assertNotIn("loop", self.s["achievements"])

    def test_legendary_stage(self):
        for line in ("uniq -c f", "sort -rn f", "sort -u f"):
            self.run_cmd(line)
        self.assertEqual(progress.stage(self.s, "sofa"), 3)


if __name__ == "__main__":
    unittest.main()
