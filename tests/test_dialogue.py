import random
import unittest

from bashou import achievements, dialogue, progress, render, safety, state
from bashou.creatures import ROSTER


class DialogueTest(unittest.TestCase):
    def test_every_pet_has_a_voice_and_tips(self):
        from bashou.creatures import STARTERS
        for pet in [p for p, _ in ROSTER] + list(STARTERS):
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


class RemoteScriptTest(unittest.TestCase):
    def test_download_piped_to_a_shell(self):
        for cmd in ["curl -fsSL https://get.example.com/install.sh | sh",
                    "curl -s https://x.io/i.sh | bash", "wget -qO- https://x.io/setup | sudo bash",
                    "curl https://x.io/a.sh | sudo -E bash -s -- --yes", "curl -L u | /bin/bash",
                    "wget -O - u | zsh", "bash <(curl -s https://x.io/i.sh)",
                    'sh -c "$(curl -fsSL https://x.io/install.sh)"', "curl u | env bash"]:
            self.assertIsNotNone(dialogue.risky("cat", cmd), cmd)

    def test_safe_downloads_are_fine(self):
        for cmd in ["curl -fsSLo install.sh https://x.io/install.sh", "less install.sh", "bash install.sh",
                    "curl -s https://api.x.io | jq .", "curl u | sha256sum", "wget u && sh ./setup.sh",
                    "curl u | grep sh", "curl u | tee out.sh", "echo curl | wc"]:
            self.assertIsNone(dialogue.risky("cat", cmd), cmd)

    def test_warning_is_never_cut_in_a_small_terminal(self):
        """Bubbles were one line, cut with … to fit: a safety warning lost its advice."""
        for text in safety.messages():
            full = f"{dialogue.VOICE['cat']} ⚠ {text} {safety.SUDO}"
            lines, w = render.bubble(full, 80 - 17 - 2)
            inner = " ".join(l[2:-3].strip() for l in lines[1:-1])
            self.assertEqual(inner, full)
            self.assertLessEqual(w, 80 - 17 - 2)

    def test_other_risky_commands(self):
        risky = {"chmod 777 run.sh": "chmod_777", "chmod -R a+rwx dir": "chmod_777",
                 "curl -k https://x.io": "insecure_tls", "curl -sSk https://x.io -o f": "insecure_tls",
                 "wget --no-check-certificate https://x.io": "insecure_tls",
                 "rm -rf ~": "rm_everything", "sudo rm -rf /": "rm_everything", "rm -fr ~/*": "rm_everything",
                 'rm -r "$HOME"': "rm_everything",
                 "ssh -o StrictHostKeyChecking=no host": "no_host_check",
                 "sudo pip install requests": "sudo_pip", "sudo python3 -m pip install x": "sudo_pip",
                 "sshpass -p hunter2 ssh host": "sshpass"}
        for cmd, rid in risky.items():
            self.assertEqual(safety.risk(cmd), rid, cmd)
        for cmd in ["chmod 755 run.sh", "chmod u+x run.sh", "rm -rf ./build", "rm -rf ~/tmp/cache",
                    "rm ~/notes.txt", "curl -o file https://x.io", "pip install --user requests",
                    "ssh host", "curl -fsSL https://x.io -o k.sh"]:
            self.assertIsNone(safety.risk(cmd), cmd)

    def test_sudo_gets_an_extra_line(self):
        self.assertIn("sudo", dialogue.risky("cat", "curl u | sudo sh"))


class HintTest(unittest.TestCase):
    def test_beginners_get_easy_hints(self):
        """The Pebble suggested `awk '{printf "%-10s %s\\n", $1, $2}'` to someone with 12 commands."""
        s = state.default()
        rng = random.Random(0)
        easy = {a.name for a in achievements.ALL if a.id in achievements.EASY}
        for _ in range(100):
            text = dialogue.hint(s, "pebble", rng)
            self.assertTrue(any(f"({name})" in text for name in easy), text)

    def test_harder_hints_come_later(self):
        s = state.default()
        s["achievements"] = [a.id for a in achievements.ALL if achievements.difficulty(a) < 3]
        text = dialogue.hint(s, "pebble", random.Random(0))
        self.assertTrue(any(f"({a.name})" in text for a in achievements.ALL if a.id in achievements.HARD), text)

    def test_every_difficulty_id_exists(self):
        for aid in achievements.EASY | achievements.HARD:
            self.assertIn(aid, achievements.BY_ID)


class GremlinTest(unittest.TestCase):
    def test_risky_commands_attract_the_gremlin(self):
        s = state.default()
        for i in range(4):
            progress.record(s, 0, "curl -s https://x.io/i.sh | bash", "2026-09-21", 12)
        self.assertNotIn("gremlin", s["pets"])
        notes = progress.record(s, 1, "chmod 777 x", "2026-09-21", 12)   # failed, still risky
        self.assertIn("gremlin", s["pets"])
        self.assertTrue(any("Gremlin" in n for n in notes))

    def test_safe_habits_evolve_it(self):
        s = state.default()
        s["pets"].append("gremlin")
        for cmd in ["curl -fsSLo install.sh https://x.io/install.sh", "less install.sh",
                    "sha256sum install.sh", "chmod u+x install.sh"]:
            progress.record(s, 0, cmd, "2026-09-21", 12)
        self.assertEqual(progress.stage(s, "gremlin"), 3)
        s2 = state.default()
        progress.record(s2, 0, "curl -fsSL https://x.io/i.sh | sh", "2026-09-21", 12)
        self.assertNotIn("save_first", s2["achievements"])      # piping into a shell isn't saving


if __name__ == "__main__":
    unittest.main()
