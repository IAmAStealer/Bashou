"""One test per bug we already hit, so it stays fixed.

Bugs covered elsewhere: sprite rows too wide (test_creatures), particle spot over the
ears (test_behavior), `$(` inside quotes / redirect targets / `while` loops (test_analyze),
hints without an example (test_dialogue), unlock message using the wrong stage name
(test_progress).
"""

import contextlib
import io
import os
import random
import tempfile
import time
import unittest
from pathlib import Path

from bashou import challenges, cli, fight, state


class TempState(unittest.TestCase):
    """Point the state at a temporary folder for the duration of a test."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = state.DATA, state.STATE
        state.DATA = Path(self.tmp.name)
        state.STATE = state.DATA / "state.json"

    def tearDown(self):
        state.DATA, state.STATE = self.saved
        self.tmp.cleanup()


class ArenaBugs(unittest.TestCase):
    def test_banner_names_the_main_tool(self):
        """The Log Hydra asked for `egrep`: tools were a set, and the "main" one was sorted()[0]."""
        expected = {"grep_hydra": "grep", "awk_golem": "awk", "find_wraith": "find",
                    "uniq_swarm": "uniq", "sed_serpent": "sed", "ps_phantom": "ps"}
        for ch in challenges.ALL:
            self.assertEqual(ch.tool, expected[ch.id])

    def test_win_is_not_a_normal_exit_code(self):
        """Ctrl-D in the arena after a successful command exited with 0, which counted as a win."""
        self.assertNotIn(fight.WIN, (0, 1, 2, 130))
        self.assertIn(f"exit {fight.WIN}", fight.RC)
        self.assertNotEqual(fight.FLEE, fight.WIN)

    def test_phantom_process_is_killed(self):
        """The ps challenge's decoy process must not outlive the arena."""
        ch = challenges.BY_ID["ps_phantom"]
        with tempfile.TemporaryDirectory() as tmp:
            meta = ch.setup(Path(tmp), random.Random(0))
        pid = meta["pid"]
        os.kill(pid, 0)                                  # alive during the fight
        ch.cleanup(meta)
        for _ in range(20):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.05)
        self.fail(f"decoy {pid} still running")


class CliBugs(TempState):
    def test_stats_is_not_empty(self):
        """`bashou stats` only showed breathing sessions, so it looked like it did nothing."""
        with state.locked() as s:
            s["commands"] = 12
            s["tools"] = {"grep": 5, "ls": 7}
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.stats()
        text = out.getvalue()
        for word in ("Commands", "12", "Top tools", "grep", "ls"):
            self.assertIn(word, text)

    def test_breathe_is_gone(self):
        """`bashou breathe` was removed on purpose; its state key must not be required."""
        self.assertNotIn("breathe", state.default())
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            import sys
            old, sys.argv = sys.argv, ["bashou", "breathe"]
            try:
                cli.main()
            finally:
                sys.argv = old

    def test_swap_board_refuses_locked_pets(self):
        """Picking a locked pet on the board must not change the active pet."""
        from bashou.board import Board
        board = Board()
        board.pos = board.ids.index("dragon")
        self.assertTrue(board.key("enter"))              # board stays open
        self.assertIn("Not unlocked", board.message)
        self.assertEqual(state.load()["active"], "starter")


class BubbleTest(TempState):
    def setUp(self):
        super().setUp()
        from bashou.companion import Companion
        self.pet = Companion(os.getpid())
        self.pet.events = state.DATA / "events.test"

    def run_commands(self, n):
        with open(self.pet.events, "a") as f:
            f.write("".join(f"0\t    {i}  true\n" for i in range(n)))
        self.pet.read_events()
        self.pet.update_bubble()

    def test_bubble_stays_for_several_commands(self):
        """Talk and hints vanished after 5 s, before you could read them."""
        self.pet.notes = ["hello"]
        self.pet.update_bubble()
        self.run_commands(4)
        self.assertEqual(self.pet.bubble[0], "hello")
        self.run_commands(6)
        self.assertNotEqual((self.pet.bubble or [""])[0], "hello")

    def test_waiting_note_shortens_the_bubble(self):
        self.pet.notes = ["first"]
        self.pet.update_bubble()
        self.pet.notes.append("second")
        self.run_commands(2)
        self.assertEqual(self.pet.bubble[0], "second")


class CodeUpdateTest(TempState):
    def test_pet_notices_new_code(self):
        """A pet started before an update kept running the old code (the starter stayed a cat)."""
        from bashou import companion
        src = Path(self.tmp.name) / "src"
        src.mkdir()
        (src / "a.py").write_text("")
        old = companion.SOURCE
        companion.SOURCE = src
        try:
            pet = companion.Companion(os.getpid(), offset=42)
            self.assertEqual(pet.offset, 42)                 # handed over, so nothing counts twice
            self.assertFalse(pet.code_changed())
            os.utime(src / "a.py", (time.time(), time.time() + 5))
            self.assertFalse(pet.code_changed())             # still being saved: wait
            os.utime(src / "a.py", (time.time() - 10, time.time() - 10))
            self.assertTrue(pet.code_changed())
        finally:
            companion.SOURCE = old


class ConfigTest(TempState):
    def test_bubble_setting(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.config("bubble", "3"), 0)
            self.assertEqual(state.setting(state.load(), "bubble"), (3, 3))
            self.assertEqual(cli.config("bubble", "8-4"), 1)          # refused, unchanged
            self.assertEqual(cli.config("bubble", "nope"), 1)
            self.assertEqual(state.setting(state.load(), "bubble"), (3, 3))
            self.assertEqual(cli.config("bubble", "default"), 0)
            self.assertEqual(state.setting(state.load(), "bubble"), (5, 10))
            self.assertEqual(cli.config("volume", "3"), 1)


class BoardTest(TempState):
    def test_starter_row_navigation(self):
        from bashou.board import Board
        board = Board()
        self.assertEqual(board.ids[board.pos], "starter")    # active pet is selected first
        board.key("down")
        self.assertEqual(board.ids[board.pos], "bat")
        board.key("up")
        self.assertEqual(board.ids[board.pos], "starter")
        board.key("up")                                      # wraps to the last row, first column
        self.assertEqual(board.ids[board.pos], "ghost")

    def test_pick_the_starter_back(self):
        from bashou.board import Board
        with state.locked() as s:
            s["starter"], s["pets"], s["active"] = "pebble", ["fox"], "fox"
        board = Board()
        board.pos = 0
        self.assertFalse(board.key("enter"))
        self.assertEqual(state.load()["active"], "starter")


if __name__ == "__main__":
    unittest.main()
