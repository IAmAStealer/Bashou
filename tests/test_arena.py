"""`bashou arena` (owner, 2026-09-26): a timed fight or a security investigation, when you want;
lose and the gates close for an hour."""

import contextlib
import io
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from bashou import arena, challenges, fight, security, state


class ArenaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = state.DATA, state.STATE, state.CACHE
        state.DATA = Path(self.tmp.name)
        state.STATE = state.DATA / "state.json"
        state.CACHE = state.DATA / "cache"

    def tearDown(self):
        state.DATA, state.STATE, state.CACHE = self.saved
        self.tmp.cleanup()

    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = arena.main(*args)
        return code, out.getvalue()

    def test_a_lost_fight_closes_the_arena_for_an_hour(self):
        with mock.patch.object(fight, "run", return_value=fight.KO):
            self.run_main("fight")
        wait = arena.closed_for(state.load())
        self.assertTrue(3500 < wait <= 3600, wait)
        with mock.patch.object(fight, "run") as run:
            code, text = self.run_main("fight")
        run.assert_not_called()
        self.assertEqual(code, 1)
        self.assertIn("60 min", text)

    def test_time_up_and_fleeing_close_it_too(self):
        for code in (fight.TIMEOUT, fight.FLEE):
            with state.locked() as s:
                s["arena_closed_until"] = 0
            with mock.patch.object(fight, "run", return_value=code):
                self.run_main("fight")
            self.assertTrue(arena.closed_for(state.load()), code)

    def test_a_win_keeps_it_open_and_the_fight_has_a_clock(self):
        with mock.patch.object(fight, "run", return_value=fight.WIN) as run:
            self.run_main("fight")
        ch = run.call_args.args[0]
        self.assertEqual(run.call_args.kwargs["limit"], arena.LIMITS[ch.level] * 60)
        self.assertEqual(arena.closed_for(state.load()), 0)

    def test_a_security_investigation_has_no_clock(self):
        with mock.patch.object(fight, "arena", return_value=(fight.FLEE, [])) as run:
            self.run_main("security", "1")
        self.assertNotIn("limit", run.call_args.kwargs)
        self.assertTrue(arena.closed_for(state.load()))        # giving up is losing

    def test_the_announced_threat_comes_first_then_reviews(self):
        s = state.default()
        s["threat"] = {"challenge": "grep_hydra", "until": time.time() + 600}
        self.assertEqual(arena.pick_fight(s).id, "grep_hydra")
        s["threat"] = None
        s["challenges"] = ["line_moth"]
        s["reviews"] = {"line_moth": {"step": 0, "due": "2000-01-01"}}
        self.assertEqual(arena.pick_fight(s).id, "line_moth")

    def test_nothing_ready_means_no_fight_and_no_closing(self):
        with mock.patch.object(arena, "pick_fight", return_value=None):
            code, text = self.run_main("fight")
        self.assertIn("bashou arena security", text)
        self.assertEqual(arena.closed_for(state.load()), 0)

    def test_old_security_command_is_the_arena(self):
        from bashou import cli
        import sys
        old, sys.argv = sys.argv, ["bashou", "security"]
        try:
            with mock.patch.object(arena, "main", return_value=0) as main, self.assertRaises(SystemExit):
                cli.main()
        finally:
            sys.argv = old
        main.assert_called_once_with("security", None)


class ClockTest(unittest.TestCase):
    def test_time_up_hangs_up_the_arena_shell(self):
        shell = subprocess.Popen(["bash", "--norc", "-i"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        with self.assertRaises(subprocess.TimeoutExpired):
            shell.wait(timeout=0.3)
        self.assertEqual(fight.stop_shell(shell), fight.TIMEOUT)
        self.assertIsNotNone(shell.poll())
        shell.stdin.close()

    def test_the_prompt_shows_the_time_left(self):
        base = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, base)
        (base / "arena").mkdir()
        (base / "arena.rc").write_text(fight.RC)
        env = {**os.environ, "BASHOU_ARENA": str(base), "BASHOU_SRC": str(Path(fight.__file__).parent.parent),
               "BASHOU_DEADLINE": str(int(time.time()) + 125)}
        env.pop("BASHOU_DUEL", None)
        out = subprocess.run(["bash", "--rcfile", str(base / "arena.rc"), "-i"], input="true\nexit 0\n",
                             capture_output=True, text=True, env=env, timeout=20)
        self.assertRegex(out.stderr, r"⏱ 2:0[0-5]")


if __name__ == "__main__":
    unittest.main()
