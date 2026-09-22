import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bashou import achievements, creatures, dialogue, progress, state


class ProgressTest(unittest.TestCase):
    def setUp(self):
        self.s = state.default()

    def run_cmd(self, line, status=0, times=1, hour=14):
        notes = []
        for _ in range(times):
            notes += progress.record(self.s, status, line, "2026-09-21", hour)
        return notes

    def test_command_milestone(self):
        """Commands grow the Slime (owner): a Droplet at 10, a new form at each count of its ladder."""
        self.assertEqual(self.run_cmd("ls", times=9), [])
        self.assertIn("Droplet", self.run_cmd("ls")[0])
        self.assertEqual(self.run_cmd("ls", times=39), [])
        notes = self.run_cmd("ls")
        self.assertEqual(notes, [])
        notes = self.run_cmd("ls", times=50)                                       # 100 commands
        self.assertIn("Droplet is evolving", " ".join(notes))
        self.assertEqual(progress.stage(self.s, "slime"), 2)
        self.assertEqual(progress.next_milestone(self.s), (200, "?"))             # no spoiler

    def test_themed_unlocks(self):
        """Milestone pets now come from what they stand for (owner)."""
        self.run_cmd("python3 app.py", times=10)
        self.assertIn("bat", self.s["pets"])
        self.run_cmd("./backup.sh", times=3)
        self.run_cmd("bash deploy.sh", times=2)
        self.assertIn("mushroom", self.s["pets"])
        self.s["adventure"] = {"walked": 500, "correct": 20}
        self.s["fights_lost"], self.s["fights_won"] = 1, 1
        progress.check(self.s)
        self.assertLessEqual({"turtle", "frog", "sofa", "dragon"}, set(self.s["pets"]))

    def test_the_slime_never_shrinks(self):
        old = {**state.default(), "commands": 20, "achievements": [a.id for a in achievements.family("slime")]}
        del old["ladder_best"]                                             # a King slime by its family
        s = state.migrate(old)
        self.assertEqual(progress.current(s, "slime")[0], "king_slime")
        self.assertEqual(progress.tier(s, "slime", progress.stage(s, "slime")), 3)

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
        self.assertIn("✨ Fennec is evolving! Watch it: `bashou evolve`", notes)
        self.assertEqual(progress.stage(self.s, "fox"), 2)
        self.assertEqual(progress.current(self.s, "fox")[1:3], (2, "Fennec"))   # new actions, old look until watched
        self.assertEqual(self.s["evolving"], [{"who": "fox", "from": 1, "to": 2}])
        progress.watched(self.s, "fox")
        self.assertEqual(progress.current(self.s, "fox")[2], "Fox")
        self.assertEqual(self.s["evolving"], [])

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

    def test_new_tool_pets(self):
        self.run_cmd("git status", times=10)
        self.assertIn("beaver", self.s["pets"])
        notes = self.run_cmd("tar -tzf a.tgz", times=10)
        self.assertIn("squirrel", self.s["pets"])
        self.assertTrue(any("tar/gzip" in n for n in notes), notes)     # a readable tool name, not "gunzip"
        self.run_cmd("watch -n 2 df -h", times=10)                     # a wrapper and its command both count
        self.assertIn("meerkat", self.s["pets"])

    def test_new_rules_need_the_right_arguments(self):
        for line in ("git log --oneline", "git checkout main", "tar -xf a.tgz", "tar -cf a.tar d",
                     "curl https://x", "ssh host", "dig example.com", "chmod +x f", "chown root f",
                     "systemctl enable cron", "kubectl get pods", "kubectl logs pod", "kubectl exec pod -- ls",
                     "du -h", "df", "watch df"):
            self.run_cmd(line)
        new = {a.id for pet in ("beaver", "squirrel", "pigeon", "hedgehog", "bee", "whale", "meerkat")
               for a in achievements.ALL if a.pet == pet}
        self.assertEqual(new & set(self.s["achievements"]), set())
        self.run_cmd("tar czf a.tgz d")                                 # no dash: still tar -czf
        self.assertIn("packer", self.s["achievements"])

    def test_pets_and_hints_need_their_command(self):
        with mock.patch("bashou.which.installed", return_value=True):     # CI runners have kubectl, this machine doesn't
            self.assertEqual(len(achievements.family("whale")), 4)
        with mock.patch("bashou.which.installed", side_effect=lambda name: name != "kubectl"):
            self.assertNotIn("whale", dict(creatures.roster()))
            self.s["pets"] = ["whale", "fox"]                             # unlocked before kubectl was removed
            self.assertEqual(creatures.owned(self.s), ["fox"])
            self.assertEqual(achievements.family("whale"), [])
            for pet in ("pigeon", "star"):
                for seed in range(30):
                    import random
                    self.assertNotIn("kubectl", dialogue.hint(self.s, pet, random.Random(seed)) or "")
        with mock.patch("bashou.which.installed", side_effect=lambda name: name != "dig"):
            self.assertEqual(progress.tool_label("pigeon"), "curl/ssh")        # the unlock hint named dig
            for seed in range(50):
                import random
                self.assertNotIn("dig ", dialogue.hint(self.s, "pigeon", random.Random(seed)) or "")
            self.assertIn("whale", dict(creatures.roster()))
            ids = {a.id for a in achievements.family("pigeon")}
            self.assertNotIn("resolver", ids)
            self.assertIn("headers", ids)
            self.s["achievements"] += list(ids)                          # legendary without the dig ones
            self.assertEqual(progress.stage(self.s, "pigeon"), 3)

    def test_legendary_stage(self):
        for line in ("uniq -c f", "sort -rn f", "sort -u f"):
            self.run_cmd(line)
        self.assertEqual(progress.stage(self.s, "sofa"), 3)


if __name__ == "__main__":
    unittest.main()


class StarterTest(unittest.TestCase):
    def test_levels_and_forms(self):
        s = state.default()
        s["starter"] = "pebble"
        self.assertEqual((progress.starter_level(s), progress.starter_form(s)), (1, 1))
        self.assertEqual(progress.current(s)[:3], ("pebble", 1, "Pebble"))
        s["achievements"] = [f"a{i}" for i in range(15)]
        self.assertEqual((progress.starter_level(s), progress.starter_form(s)), (4, 1))
        s["achievements"] = [f"a{i}" for i in range(35)]
        self.assertEqual((progress.starter_level(s), progress.starter_form(s)), (8, 2))
        self.assertEqual(progress.current(s)[2], "Rock golem")
        s["achievements"] = [f"a{i}" for i in range(94)]
        self.assertEqual(progress.starter_level(s), progress.MAX_LEVEL - 1)
        s["achievements"] = [f"a{i}" for i in range(99)]
        self.assertEqual(progress.starter_level(s), progress.MAX_LEVEL)
        self.assertEqual(progress.current(s)[:3], ("crystal", 3, "Crystal golem"))

    def test_level_up_and_evolution_notes(self):
        s = state.default()
        s["starter"] = "star"
        s["achievements"] = [f"a{i}" for i in range(4)]
        notes = progress.check(s, [a for a in __import__("bashou").achievements.ALL[:1]])
        self.assertIn("⬆ Stardust reached level 2!", notes)
        s["achievements"] = [f"a{i}" for i in range(14)]
        notes = progress.check(s, [a for a in __import__("bashou").achievements.ALL[:1]])
        self.assertIn("✨ Stardust is evolving! Watch it: `bashou evolve`", notes)
        self.assertEqual(progress.current(s)[:3], ("stardust", 1, "Stardust"))     # a Comet: still tier 1
        s["achievements"] = [f"a{i}" for i in range(34)]                   # to Planet (level 8) before watching
        progress.check(s, [a for a in __import__("bashou").achievements.ALL[:1]])
        self.assertEqual(s["evolving"], [{"who": "starter", "from": 1, "to": 3}])   # one animation, Stardust → Planet

    def test_pick_an_earlier_look(self):
        s = state.default()
        s["starter"], s["achievements"] = "star", [f"a{i}" for i in range(45)]
        self.assertEqual(progress.current(s)[:3], ("star", 3, "Star"))
        s["looks"]["starter"] = 1
        self.assertEqual(progress.current(s)[:3], ("stardust", 3, "Stardust"))   # stardust that can dance
        s["looks"]["starter"] = 9
        self.assertEqual(progress.look(s), 4)                                   # never beyond what's reached

    def test_old_saves_keep_the_cat_as_starter(self):
        s = state.migrate({**state.default(), "pets": ["cat", "fox"], "active": "cat"})
        self.assertEqual((s["starter"], s["pets"], s["active"]), ("star", ["fox"], "starter"))

    def test_the_cat_starter_becomes_the_star(self):
        old = {**state.default(), "starter": "cat", "achievements": ["a"] * 20}
        del old["starter_best"]                                            # saved before long ladders
        s = state.migrate(old)
        self.assertEqual(s["starter"], "star")
        self.assertEqual(progress.current(s)[:3], ("planet", 2, "Planet"))

    def test_old_saves_never_lose_their_form(self):
        """0.2.3 saves: a Planet at level 5 (now the Comet's level) stays a Planet until the Star."""
        for achieved, looks, sprite in ((20, {}, "planet"), (40, {}, "star"), (40, {"starter": 2}, "planet"),
                                        (10, {}, "stardust")):
            with self.subTest(achieved=achieved, looks=looks):
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "state.json"
                    path.write_text(json.dumps({"starter": "star", "looks": looks,
                                                "achievements": [f"a{i}" for i in range(achieved)]}))
                    with mock.patch.object(state, "STATE", path):
                        s = state.load()
                self.assertEqual(progress.current(s)[0], sprite)
        s["achievements"] = [f"a{i}" for i in range(45)]                   # level 10: the Star comes
        self.assertEqual(progress.starter_form(s), 4)

    def test_evolving_saved_before_long_ladders(self):
        old = {**state.default(), "starter": "star", "achievements": ["a"] * 15,
               "evolving": [{"who": "starter", "from": 1, "to": 2}], "looks": {"starter": 1}}
        del old["starter_best"]
        s = state.migrate(old)
        self.assertEqual(s["evolving"], [{"who": "starter", "from": 1, "to": 3}])      # Stardust → Planet still
        self.assertEqual(progress.starter_form(s), 3)
