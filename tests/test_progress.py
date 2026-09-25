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
        old = {**state.default(), "commands": 20,
               "achievements": ["capture", "nested", "substitute", "here"]}      # its family until 0.2.3
        del old["ladder_best"]                                             # a King slime by its family
        s = state.migrate(old)
        self.assertEqual(progress.current(s, "slime")[0], "king_slime")
        self.assertEqual(progress.tier(s, "slime", progress.stage(s, "slime")), 3)

    def test_new_slime_forms_keep_old_ones(self):
        """0.4.3 added the Ice slime (3,500) and the Thunder slime (7,500): a King slime stays a King."""
        for best, form in ((5, "rock_slime"), (6, "cat_slime"), (7, "king_slime")):
            old = {**state.default(), "version": 2, "commands": 20, "ladder_best": {"slime": best}}
            self.assertEqual(progress.current(state.migrate(old), "slime")[0], form)
        s = {**state.default(), "commands": 3500}
        self.assertEqual(progress.current(s, "slime")[0], "ice_slime")
        s["commands"] = 7500
        self.assertEqual(progress.current(s, "slime")[0], "thunder_slime")

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

    def test_secrets_bring_the_snow_leopard(self):
        self.run_cmd("gpg -c notes.txt")
        self.assertIn("sealed", self.s["achievements"])
        self.run_cmd("pass show web/forum", times=4)
        self.assertIn("leopard", self.s["pets"])
        self.assertNotIn("keeper", self.s["achievements"])                     # printed, not handed to a command
        self.run_cmd('curl -u "me:$(pass show web/api)" https://example.org')
        self.assertIn("keeper", self.s["achievements"])

    def test_debugging_brings_the_duck(self):
        """Owner: "ducks are awesome". Rubber-duck debugging: explain, trace, check the exit code."""
        self.run_cmd("bash script.sh")
        self.assertNotIn("duck", self.s["pets"])
        notes = self.run_cmd("bash -x script.sh")
        self.assertIn("xray", self.s["achievements"])
        self.assertIn("duck", self.s["pets"])
        self.assertTrue(any("Duckling" in n for n in notes), notes)
        self.run_cmd("ls /nope; echo $?")
        self.assertIn("exit_code", self.s["achievements"])

    def test_the_duck_takes_a_form_per_achievement(self):
        """Four forms (owner: a White duck, then a Mandarin duck): one per achievement, the last when all are done."""
        from bashou import creatures
        with mock.patch("bashou.which.installed", side_effect=lambda name: name != "shellcheck"):
            seen = []
            for line in ("bashou learn", "bash -x a.sh", "bash -n a.sh", "ls; echo $?"):
                self.run_cmd(line)
                seen.append(creatures.form("duck", progress.stage(self.s, "duck")))
        self.assertEqual(seen, ["duckling", "duck", "white_duck", "mandarin_duck"])

    def test_lessons_bring_the_spark_up_to_the_phoenix(self):
        """Owner: the lesson achievements belong to a fire pet (the Library of Alexandria burned; what you
        learn, nobody can burn). Sparklings first, the Phoenix is the endgame, ten forms in all."""
        from bashou import challenges, creatures, lesson
        every = [le["id"] for le in lesson.english()]
        seen = []

        def read(*ids):
            self.s["lessons"]["read"] += [i for i in ids if i not in self.s["lessons"]["read"]]
            notes = progress.check(self.s)
            seen.append(creatures.form("spark", progress.stage(self.s, "spark")))
            return notes

        self.assertNotIn("spark", self.s["pets"])
        notes = read("command_line")
        self.assertIn("spark", self.s["pets"])
        self.assertTrue(any("Sparklings" in n for n in notes), notes)
        read("paths", "streams")                                          # 3 read: Page turner
        self.s["challenges"] += ["semicolon_slug", "leak_lurker", "stack_specter"]
        read("stack_heap")                                                # mastered, and a 3rd skill
        read("pipes", "permissions")                                      # 6: Bookworm
        self.s["challenges"] += [c.id for c in challenges.ALL if c.id not in self.s["challenges"]]
        read("pointers", "py_names", "sql_join", "pipeline", "rust_vars")  # 5 mastered: Librarian
        read(*every[:12])                                                 # 12: Scholar, 10 mastered: Torchbearer
        read(*every[:20])                                                 # 20: Well read
        read(*every)                                                      # every one: Alexandria
        self.assertEqual(seen, ["sparklings", "spark", "candle", "lantern", "torch", "campfire",
                                "beacon", "phoenix"])                    # 2 at once skip the Ember and the Blaze
        self.assertEqual(len(creatures.FORMS["spark"]), 10)

    def test_one_skill_can_reach_the_phoenix(self):
        """Read 20, master 10, three skills: a player who only learns Rust has fewer lessons than that,
        and the Phoenix must not be out of reach."""
        from bashou import achievements, creatures, lesson
        self.s["skills"] = ["rust"]
        self.s["achievements"] += [a.id for a in achievements.ALL if a.pet != "spark"]
        self.s.update(commands=500, fights_won=4)
        self.s["tools"].update(less=3, tail=3, ls=50)
        self.s["challenges"] += ["mut_marmot", "const_condor", "shadow_shade", "byte_basilisk"]
        self.s["lessons"]["read"] = [le["id"] for le in lesson.shown(self.s, lesson.english())]
        progress.check(self.s)
        self.assertEqual(creatures.form("spark", progress.stage(self.s, "spark")), "phoenix")

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
        self.assertEqual(progress.current(s)[:3], ("sand_grain", 1, "Sand grain"))
        s["achievements"] = [f"a{i}" for i in range(15)]
        self.assertEqual((progress.starter_level(s), progress.starter_form(s)), (4, 2))   # Gravel at level 3
        s["achievements"] = [f"a{i}" for i in range(50)]
        self.assertEqual((progress.starter_level(s), progress.starter_form(s)), (11, 5))
        self.assertEqual(progress.current(s)[2], "Rock golem")
        s["achievements"] = [f"a{i}" for i in range(94)]
        self.assertEqual(progress.starter_level(s), progress.MAX_LEVEL - 1)
        s["achievements"] = [f"a{i}" for i in range(99)]
        self.assertEqual(progress.starter_level(s), progress.MAX_LEVEL)
        self.assertEqual(progress.current(s)[:3], ("jade_golem", 3, "Jade golem"))

    def test_level_up_and_evolution_notes(self):
        s = state.default()
        s["starter"] = "star"
        s["achievements"] = [f"a{i}" for i in range(4)]
        notes = progress.check(s, [a for a in __import__("bashou").achievements.ALL[:1]])
        self.assertIn("⬆ Stardust reached level 2!", notes)
        s["achievements"] = [f"a{i}" for i in range(9)]
        notes = progress.check(s, [a for a in __import__("bashou").achievements.ALL[:1]])
        self.assertIn("✨ Stardust is evolving! Watch it: `bashou evolve`", notes)
        self.assertEqual(progress.current(s)[:3], ("stardust", 1, "Stardust"))     # a Comet: still tier 1
        s["achievements"] = [f"a{i}" for i in range(19)]                   # to Comet (level 5) before watching
        progress.check(s, [a for a in __import__("bashou").achievements.ALL[:1]])
        self.assertEqual(s["evolving"], [{"who": "starter", "from": 1, "to": 3}])   # one animation, Stardust → Comet

    def test_pick_an_earlier_look(self):
        s = state.default()
        s["starter"], s["achievements"] = "star", [f"a{i}" for i in range(95)]
        self.assertEqual(progress.current(s)[:3], ("red_giant", 3, "Red giant"))
        s["looks"]["starter"] = 1
        self.assertEqual(progress.current(s)[:3], ("stardust", 3, "Stardust"))   # stardust that can dance
        s["looks"]["starter"] = 9
        self.assertEqual(progress.look(s), 7)                                   # never beyond what's reached

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
                                        (10, {}, "meteor")):
            with self.subTest(achieved=achieved, looks=looks):
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "state.json"
                    path.write_text(json.dumps({"starter": "star", "looks": looks,
                                                "achievements": [f"a{i}" for i in range(achieved)]}))
                    with mock.patch.object(state, "STATE", path):
                        s = state.load()
                self.assertEqual(progress.current(s)[0], sprite)
        s["achievements"] = [f"a{i}" for i in range(70)]                   # level 15: the Star comes
        self.assertEqual(progress.starter_form(s), 6)

    def test_pre_release_save_loads(self):
        """A save from before v0.1.0 (installs that updated with git pull) keeps its progress."""
        old = {"version": 1, "commands": 50, "tools": {"ls": 9}, "constructs": {"pipe3": 1},
               "days": ["2026-09-20"], "today": {"date": "2026-09-20", "count": 4}, "language": "en",
               "starter": "cat", "pets": ["cat", "fox"], "active": "fox", "achievements": ["tally"],
               "fights_won": 2, "challenges": ["pipe"], "threat": None,
               "threat_day": {"date": "", "count": 0}, "last_threat": 0, "update_checked": 0,
               "update_behind": 3, "settings": {"bubble": [5, 10]}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text(json.dumps(old))
            with mock.patch.object(state, "STATE", path):
                s = state.load()
        self.assertEqual((s["starter"], s["pets"], s["active"]), ("star", ["fox"], "fox"))
        self.assertEqual((s["commands"], s["achievements"], s["challenges"]), (50, ["tally"], ["pipe"]))
        self.assertEqual(s["skills"], "all")
        progress.current(s)

    def test_evolving_saved_before_long_ladders(self):
        old = {**state.default(), "starter": "star", "achievements": ["a"] * 15,
               "evolving": [{"who": "starter", "from": 1, "to": 2}], "looks": {"starter": 1}}
        del old["starter_best"]
        s = state.migrate(old)
        self.assertEqual(s["evolving"], [{"who": "starter", "from": 1, "to": 5}])      # Stardust → Planet still
        self.assertEqual(progress.starter_form(s), 5)
