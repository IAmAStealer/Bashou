import json
import os
import random
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bashou import challenges, duel, fight, state
from tests.test_fight import SOLUTIONS
from tests.test_regressions import TempState


def arena(ch_id):
    """A fake arena folder for `ch_id`: (base, meta)."""
    base = Path(tempfile.mkdtemp())
    (base / "arena").mkdir()
    meta = {"challenge": ch_id, "hints": 0, **challenges.BY_ID[ch_id].setup(base / "arena", random.Random(0))}
    (base / "meta.json").write_text(json.dumps(meta))
    return base, meta


def log(base, *records):
    with open(base / "log", "a") as f:
        for status, cmd in records:
            f.write(f"{status}\t  1  {cmd}\n")


class JudgeTest(unittest.TestCase):
    def test_the_lesson_hits_other_tools_hurt_looking_is_free(self):
        hydra = challenges.BY_ID["grep_hydra"]
        self.assertEqual(duel.judge(hydra, 0, "grep -c ERROR app.log"), "hit")
        self.assertEqual(duel.judge(hydra, 0, "cat app.log | grep ERROR"), "hit")
        self.assertEqual(duel.judge(hydra, 2, "grep -c ERROR nope.log"), "hurt")      # missed
        self.assertEqual(duel.judge(hydra, 0, "awk '/ERROR/' app.log"), "hurt")       # not the lesson
        for free in ("ls -la", "cat app.log", "cd ..", "head -3 app.log", "hint", "task", "answer 3"):
            self.assertIsNone(duel.judge(hydra, 0, free), free)

    def test_every_reference_solution_hits(self):
        for ch in challenges.ALL:
            cmd = SOLUTIONS[ch.id][0].replace("{x}", "x").replace("{{", "{").replace("}}", "}")
            if ch.verify and ch in challenges.code.ALL:                  # fix fights: edit, then run it
                cmd = "gcc prog.c -o prog" if "gcc" in ch.tools else "python3 prog.py"
            if ch.tool == "nano":                                        # repository files: edit them
                cmd = "nano the.repo"
            self.assertEqual(duel.judge(ch, 0, cmd), "hit", ch.id)


    def test_code_fights(self):
        """Fix fights: opening an editor is free, building or running your program hits."""
        leech, slug = challenges.BY_ID["list_leech"], challenges.BY_ID["semicolon_slug"]
        self.assertIsNone(duel.judge(leech, 0, "nano hosts.py"))
        self.assertEqual(duel.judge(leech, 1, "python3 hosts.py"), "hurt")
        self.assertEqual(duel.judge(slug, 0, "./hello"), "hit")
        self.assertEqual(duel.judge(slug, 0, "gcc hello.c -o hello && ./hello"), "hit")


class ScoreTest(TempState):
    def setUp(self):
        super().setUp()
        self.base, self.meta = arena("grep_hydra")

    def test_hits_wear_the_enemy_down_but_answer_lands_the_last_blow(self):
        for _ in range(4):
            log(self.base, (0, "grep ERROR app.log"))
            self.assertEqual(duel.cmd_judge(self.base), 0)
        d = duel.load(self.base)
        self.assertEqual((d["enemy"], d["hearts"], d["event"]), (1, duel.HEARTS, "hit"))

    def test_three_wrong_commands_knock_you_out(self):
        log(self.base, (0, "ls"), (0, "awk 1 app.log"))
        self.assertEqual(duel.cmd_judge(self.base), 0)
        log(self.base, (0, "sed -n 1p app.log"))
        self.assertEqual(duel.cmd_judge(self.base), 0)
        self.assertEqual(duel.load(self.base)["hearts"], 1)
        log(self.base, (1, "grep"))
        self.assertEqual(duel.cmd_judge(self.base), duel.KO)

    def test_each_command_is_judged_once(self):
        log(self.base, (0, "awk 1 app.log"))
        duel.cmd_judge(self.base)
        duel.cmd_judge(self.base)                          # an empty Enter: nothing new
        self.assertEqual(duel.load(self.base)["hearts"], duel.HEARTS - 1)

    def test_the_panel_draws_and_flashes(self):
        scene = duel.Scene(self.base, 0)
        body, erase = scene.frame(120, 0)
        self.assertIn("♥♥♥", body)
        self.assertIn("app.log", body.replace("\x1b", " "))          # the task, reminded
        log(self.base, (0, "grep ERROR app.log"))
        duel.cmd_judge(self.base)
        at = duel.load(self.base)["at"]
        self.assertIn("255;255;255", scene.frame(120, at)[0])        # the enemy flashes white
        self.assertNotEqual(scene.frame(120, at)[0], scene.frame(120, at + 5)[0])
        self.assertTrue(scene.fits(80))
        self.assertTrue(erase)


class ArenaShellTest(TempState):
    """The real arena bash: wrong commands end it with a knockout."""

    def run_arena(self, commands, duel_on=True):
        base, _meta = arena("grep_hydra")
        (base / "arena.rc").write_text(fight.RC)
        env = {**os.environ, "BASHOU_ARENA": str(base), "HOME": str(base),
               "BASHOU_SRC": str(Path(fight.__file__).resolve().parent.parent)}
        if duel_on:
            env["BASHOU_DUEL"] = "1"
        return subprocess.run(["bash", "--rcfile", str(base / "arena.rc"), "-i"], input="\n".join(commands) + "\n",
                              env=env, capture_output=True, text=True, timeout=30).returncode

    def test_knocked_out(self):
        self.assertEqual(self.run_arena(["ls", "awk 1 app.log", "sed 1d app.log", "wc -l app.log", "echo still"]),
                         duel.KO)

    def test_without_the_duel_nothing_hurts(self):
        self.assertEqual(self.run_arena(["awk 1 app.log", "sed 1d app.log", "wc -l app.log", "flee"], duel_on=False),
                         fight.FLEE)

    def test_a_knockout_is_a_flee(self):
        with state.locked() as s:
            s["threat"] = {"challenge": "grep_hydra", "until": 9e9}
        with mock.patch.object(fight, "arena", return_value=(duel.KO, [])), \
                mock.patch("builtins.print") as out:
            fight.run()
        self.assertIn("Knocked out", " ".join(str(c) for c in out.call_args_list))
        self.assertEqual(state.load()["fights_won"], 0)
        self.assertIsNotNone(state.load()["threat"])


if __name__ == "__main__":
    unittest.main()
