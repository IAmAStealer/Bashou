"""Families run on achievements (owner, 2026-10-16): the 1st achievement of a family brings its pet, form k
needs T(k) = (k + 2) ** 2 // 4 - 1 of them, and the last achievement brings the last form."""

import unittest

from bashou import achievements, creatures, progress, state


def T(k):
    return (k + 2) ** 2 // 4 - 1


def achievement_families():
    """Every family that grows with achievements: not the starters, the secret Cat or the ponies."""
    return [pet for pet in creatures.NAMES
            if not creatures.FAMILIES[pet].herd and pet != "cat"]


class FormulaTest(unittest.TestCase):
    def test_the_owners_numbers(self):
        self.assertEqual([T(k) for k in range(1, 11)], [1, 3, 5, 8, 11, 15, 19, 24, 29, 35])

    def test_the_last_achievement_brings_the_last_form(self):
        wrong = {pet: (sum(a.pet == pet for a in achievements.ALL), T(len(creatures.FORMS[pet])))
                 for pet in achievement_families()
                 if sum(a.pet == pet for a in achievements.ALL) != T(len(creatures.FORMS[pet]))}
        self.assertEqual(wrong, {}, "pet: (achievements, T(forms)): add achievements or draw forms")

    def test_each_form_needs_T_of_the_next(self):
        for pet in achievement_families():
            forms = creatures.FORMS[pet]
            for k, sprite in enumerate(forms[:-1], 1):
                self.assertEqual(creatures.PETS[sprite].next_at, {"achievements": T(k + 1)}, sprite)

    def test_the_first_achievement_brings_the_pet(self):
        for pet in achievement_families():
            self.assertIn("family_achievement", creatures.FAMILIES[pet].unlock, pet)


class OwnerReportTest(unittest.TestCase):
    def setUp(self):
        self.s = state.default()

    def run_cmd(self, line, times=1):
        notes = []
        for _ in range(times):
            notes += progress.record(self.s, 0, line, "2026-10-16", 14)
        return notes

    def test_frog_achievements_bring_the_frog(self):
        """Owner: Sprinter, Historian and Thousand earned, and still no Frog."""
        self.s["achievements"] += ["sprinter", "historian", "thousand"]
        progress.check(self.s)
        self.assertIn("frog", self.s["pets"])
        self.assertEqual(progress.reached(self.s, "frog"), 2)                      # 3 achievements: T(2)

    def test_a_loop_brings_the_mushroom(self):
        notes = self.run_cmd("for f in *; do echo $f; done")
        self.assertIn("mushroom", self.s["pets"])
        self.assertTrue(any("🎉" in n for n in notes))

    def test_using_a_tool_ten_times_is_an_achievement(self):
        self.run_cmd("find . -name x", times=9)
        self.assertNotIn("fox", self.s["pets"])
        self.run_cmd("find . -name x")
        self.assertIn("fox", self.s["pets"])
        tier = [a for a in achievements.family("fox") if a.id in self.s["achievements"]]
        self.assertEqual(len(tier), 1)
        self.assertTrue(tier[0].next, "a count tier leads to the next one")

    def test_the_hint_of_a_locked_pet_shows_where_you_stand(self):
        self.run_cmd("find . -name x", times=3)
        self.assertIn("3/10", progress.how_to_unlock(self.s, "fox"))

    def test_the_slime_has_its_substitutions_back(self):
        for aid in ("capture", "nested", "substitute", "here"):
            self.assertEqual(achievements.BY_ID[aid].pet, "slime")

    def test_ten_commands_still_bring_the_slime(self):
        self.run_cmd("ls", times=9)
        self.assertNotIn("slime", self.s["pets"])
        self.run_cmd("ls")
        self.assertIn("slime", self.s["pets"])


class SaveTest(unittest.TestCase):
    def test_a_form_reached_under_the_old_rules_stays(self):
        """Version 5 saves: a Fox with its 4 old achievements was a Fox (form 3: 'all'). Its family grew,
        and it keeps its form."""
        s = state.default()
        s["version"] = 5
        s["pets"].append("fox")
        s["achievements"] += ["time_traveller", "executor", "pruner", "tracker"]
        saved = dict(s)
        state.migrate(s, saved)
        self.assertEqual(progress.reached(s, "fox"), 3)

    def test_forms_never_go_back(self):
        s = state.default()
        s["pets"].append("frog")
        s["achievements"] += ["sprinter", "historian", "thousand"]
        progress.check(s)
        s["achievements"].remove("thousand")                                      # an achievement removed
        progress.check(s)
        self.assertEqual(progress.reached(s, "frog"), 2)


if __name__ == "__main__":
    unittest.main()
