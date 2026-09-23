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
from unittest import mock
from pathlib import Path

from bashou import challenges, cli, creatures, fight, state


class TempState(unittest.TestCase):
    """Point the state at a temporary folder for the duration of a test."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = state.DATA, state.STATE, state.CACHE
        state.DATA = Path(self.tmp.name)
        state.STATE = state.DATA / "state.json"
        state.CACHE = state.DATA / "cache"

    def tearDown(self):
        state.DATA, state.STATE, state.CACHE = self.saved
        self.tmp.cleanup()


class ArenaBugs(unittest.TestCase):
    def test_banner_names_the_main_tool(self):
        """The Log Hydra asked for `egrep`: tools were a set, and the "main" one was sorted()[0]."""
        expected = {"first_line_imp": "head", "needle_gnat": "grep", "field_wasp": "awk",
                    "dust_bunny": "ls", "verse_viper": "sed", "peak_harpy": "sort",
                    "line_moth": "wc", "column_crab": "cut", "jumble_sprite": "sort",
                    "last_word_wisp": "tail", "grep_hydra": "grep", "awk_golem": "awk", "find_wraith": "find",
                    "uniq_swarm": "uniq", "sed_serpent": "sed", "ps_phantom": "ps",
                    "pipe_eel": "|"}
        expected.update({ch.id: "gcc" if "gcc" in ch.tools else "python3" for ch in challenges.code.ALL})
        expected.update({ch.id: "apt" if "apt" in ch.tools else "rpm" for ch in challenges.packages.ALL})
        expected.update({"mirror_mimic": "nano", "repo_revenant": "nano", "enabled_ettin": "dnf"})
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


class ScrollTrailTest(unittest.TestCase):
    def test_cells_above_the_pet_are_painted(self):
        """Enter on an empty line scrolled the pet up without erasing it: the Pebble left stripes above it."""
        from bashou import creatures, render
        for pet in creatures.PETS.values():
            cells = render.mask(pet)
            for r in range(1, len(cells)):
                for c, on in enumerate(cells[r]):
                    if on:
                        self.assertTrue(cells[r - 1][c], f"{pet.id}: row {r - 1}, col {c} left transparent")


class SizeTest(TempState):
    def test_large_sprite_only_where_it_fits(self):
        from bashou.companion import Companion
        pet = Companion(os.getpid())
        pet.sprite, pet.size = "tarantula", "large"
        pet.fit(200)
        self.assertIs(pet.pet, creatures.LARGE["tarantula"])
        pet.fit(60)                                              # too narrow: back to the small one
        self.assertIs(pet.pet, creatures.PETS["tarantula"])
        pet.sprite = "fox"
        pet.fit(200)                                             # no big art: small
        self.assertIs(pet.pet, creatures.PETS["fox"])


class BubbleTest(TempState):
    def setUp(self):
        super().setUp()
        from bashou.companion import Companion
        self.pet = Companion(os.getpid())
        self.pet.events = state.DATA / "events.test"

    def run_commands(self, n):
        with open(self.pet.events, "a") as f:
            f.write("".join(f"0\t    {i}  true\n" for i in range(n)))
        mine = list(self.pet.notes)
        self.pet.read_events()
        self.pet.notes = mine                    # not the notes those commands earned (Night owl after midnight…)
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
            pet = companion.Companion(os.getpid())
            self.assertFalse(pet.code_changed())
            os.utime(src / "a.py", (time.time(), time.time() + 5))
            self.assertFalse(pet.code_changed())             # still being saved: wait
            os.utime(src / "a.py", (time.time() - 10, time.time() - 10))
            self.assertTrue(pet.code_changed())
        finally:
            companion.SOURCE = old


    def test_pet_notices_new_sprites_and_translations(self):
        """An update that only changed JSON (sprites, locales) left running pets on the old ones."""
        from bashou import companion
        src = Path(self.tmp.name) / "src"
        src.mkdir()
        (src / "a.py").write_text("")
        (src / "pet.json").write_text("{}")
        past = time.time() - 100
        for f in ("a.py", "pet.json"):
            os.utime(src / f, (past, past))
        old = companion.SOURCE
        companion.SOURCE = src
        try:
            pet = companion.Companion(os.getpid())
            os.utime(src / "pet.json", (past + 50, past + 50))
            self.assertTrue(pet.code_changed())
        finally:
            companion.SOURCE = old


class ResumeTest(TempState):
    def test_restart_keeps_the_bubble(self):
        """Every code change restarted the pet and wiped the bubble after a few seconds."""
        from bashou import companion
        old = state.CACHE
        state.CACHE = Path(self.tmp.name)
        try:
            pet = companion.Companion(os.getpid())
            pet.offset, pet.bubble, pet.notes = 42, ("hello", 1, 7), ["next"]
            pet.save_resume()
            again = companion.Companion(os.getpid())
            self.assertEqual((again.offset, again.bubble, again.notes), (42, ("hello", 1, 7), ["next"]))
            self.assertFalse(again.resume_file.exists())    # used once
        finally:
            state.CACHE = old


class ThreatBubbleTest(TempState):
    def setUp(self):
        super().setUp()
        from bashou import companion
        with state.locked() as s:
            s["starter"] = "pebble"
            s["threat"] = {"challenge": "grep_hydra", "until": time.time() + 600}
        self.pet = companion.Companion(os.getpid())
        self.pet.reload_pet()                              # a terminal that didn't roll it announces it too
        self.pet.update_bubble()

    def end_threat(self, won=False):
        time.sleep(0.01)                                   # a new mtime for the state file
        with state.locked() as s:
            s["threat"] = None
            s["fights_won"] += won
        self.pet.reload_pet()
        self.pet.update_bubble()

    def test_announcement_leaves_with_the_threat(self):
        """The Log Hydra's bubble stayed up for 1h40 after it left: `bashou fight` said no threat."""
        self.assertIn("Log Hydra is coming", self.pet.bubble[0])
        self.end_threat()
        self.assertNotIn("is coming", self.pet.bubble[0])
        self.assertIn("got tired of waiting", self.pet.bubble[0])

    def test_warning_goes_when_the_threat_times_out(self):
        """The ⚠ stayed on with nothing written in the state file when the threat timed out."""
        self.assertTrue(self.pet.threat)
        self.pet.threat_until = time.time() - 1
        with state.locked() as s:
            s["threat"]["until"] = self.pet.threat_until
        self.pet.state_mtime = state.STATE.stat().st_mtime  # as if already read
        self.pet.reload_pet()
        self.assertFalse(self.pet.threat)

    def test_no_goodbye_after_a_win(self):
        self.end_threat(won=True)
        self.assertIsNone(self.pet.bubble)


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
            self.assertEqual(cli.config("updates", "maybe"), 1)
            self.assertEqual(cli.config("updates", "off"), 0)
            self.assertEqual(state.setting(state.load(), "updates"), "off")
            self.assertEqual(cli.config("size", "huge"), 1)
            self.assertEqual(cli.config("size", "large"), 0)
            self.assertEqual(state.setting(state.load(), "size"), "large")


class BoardTest(TempState):
    @mock.patch("bashou.which.installed", return_value=True)       # every pet, so the grid is fixed
    def test_starter_row_navigation(self, _):
        from bashou.board import Board
        board = Board()
        self.assertEqual(board.ids[board.pos], "starter")    # active pet is selected first
        board.key("down")
        self.assertEqual(board.ids[board.pos], "bat")
        board.key("up")
        self.assertEqual(board.ids[board.pos], "starter")
        board.key("up")                                      # wraps to the last row, first column
        self.assertEqual(board.ids[board.pos], "meerkat")
        board.pos = board.ids.index("whale")
        board.key("down")                                    # nothing below: the last row's last pet
        self.assertEqual(board.ids[board.pos], "meerkat")
        board.key("down")
        self.assertEqual(board.ids[board.pos], "starter")

    @mock.patch("bashou.which.installed", return_value=True)
    def test_board_fits_a_small_terminal(self, _):
        """At 80×24 the preview went below the grid and ran off the screen."""
        from bashou.board import COLS, Board
        board = Board()
        for pos in range(len(board.ids)):
            board.pos = pos
            grid, preview, side = board.layout(80, 24)
            self.assertFalse(side)
            self.assertLessEqual(len(grid) + 1 + len(preview), 24)
            shown = (len(grid) - 5) // 2                             # pet rows on screen
            if pos:
                self.assertTrue(board.top <= (pos - 1) // COLS < board.top + shown, pos)
        grid, preview, side = board.layout(140, 40)                   # big terminal: everything, side by side
        self.assertTrue(side)
        self.assertEqual(len(grid), 4 + board.rows() * 2 + 1)

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


class QuietTest(unittest.TestCase):
    """The pet chatted in the middle of work; it must wait for a pause first (owner)."""

    def companion(self):
        from bashou import companion
        c = companion.Companion.__new__(companion.Companion)
        c.notes, c.bubble, c.talk_at = [], None, 0
        c.behavior = type("B", (), {"mood": "awake"})()
        c.voice, c.last_command = "star", 0
        c.last_activity = lambda: c.last_command
        return c

    def test_it_waits_for_a_pause(self):
        c, now, s = self.companion(), 30 * 60_000, state.default()
        quiet = state.setting(s, "quiet")[0] * 1000
        with mock.patch.object(state, "load", return_value=s):
            c.last_command = now - 10_000                      # a command 10 s ago: still working
            c.maybe_talk(now)
            self.assertEqual(c.notes, [])
            self.assertEqual(c.talk_at, now + quiet)
            c.last_command = now - quiet - 1                   # a real pause
            c.maybe_talk(c.talk_at)
            self.assertEqual(len(c.notes), 1)

    def test_talk_off_keeps_it_quiet(self):
        c, s = self.companion(), {**state.default(), "settings": {"talk": "off"}}
        with mock.patch.object(state, "load", return_value=s):
            c.last_command = -10 * 60_000                      # long pause: it would talk otherwise
            c.maybe_talk(0)
        self.assertEqual(c.notes, [])


class PanelPercentTest(unittest.TestCase):
    def test_percent_in_a_question(self):
        """A question with `date +%F` crashed the adventure panel (text went through % formatting)."""
        from bashou.adventure import Game
        line = ("backup-$(date +%F).tar.gz", (200, 200, 200))
        out = Game(80, 30).panel_text([line], (1, 1, 40, [line]))
        self.assertIn("date +%F", out)
