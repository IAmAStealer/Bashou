import contextlib
import io
import unittest

from bashou import achievements, evolve, progress, state
from tests.test_regressions import TempState


def evolving_stardust():
    s = state.default()
    s["starter"], s["achievements"] = "star", [f"a{i}" for i in range(14)]
    progress.check(s, achievements.ALL[:1])                              # the 15th: level 4, the Comet
    return s


class AnimationTest(unittest.TestCase):
    def test_old_and_new_shapes_then_the_new_pet(self):
        s = evolving_stardust()
        shown, waits = [], []
        self.assertTrue(evolve.play(s, s["evolving"][0], lambda *f: shown.append(f), lambda t: waits.append(t)))
        self.assertIn("Stardust is evolving", shown[0][0])
        self.assertGreater(len(shown), 10)
        self.assertEqual(waits, sorted(waits[:1]) + waits[1:])            # starts slow…
        self.assertLess(min(waits), 0.1)                                   # …ends fast
        self.assertIn("Stardust evolved into", shown[-1][2])
        self.assertIn("Comet", shown[-1][2])

    def test_s_skips_to_the_end(self):
        s = evolving_stardust()
        shown = []
        keys = iter([None, "s"])
        evolve.play(s, s["evolving"][0], lambda *f: shown.append(f), lambda t: next(keys, None))
        self.assertEqual(len(shown), 3)                                   # first frame, one more, then the end
        self.assertIn("evolved into", shown[-1][2])


class EvolveCommandTest(TempState):
    def test_watching_shows_the_new_form(self):
        with state.locked() as s:
            s.update(evolving_stardust())
        self.assertEqual(progress.current(state.load())[2], "Stardust")      # no spoiler before watching
        with contextlib.redirect_stdout(io.StringIO()):
            evolve.main()                                                 # not a tty: no animation, just the news
        s = state.load()
        self.assertEqual((s["evolving"], progress.current(s)[2]), ([], "Comet"))

    def test_nothing_waiting(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(evolve.main(), 0)


class FormSwitchTest(TempState):
    def test_f_cycles_the_forms_reached(self):
        from bashou.board import Board
        with state.locked() as s:
            s["starter"], s["achievements"] = "star", [f"a{i}" for i in range(45)]
        board = Board()
        board.pos = 0
        names = []
        for _ in range(4):
            board.key("form")
            names.append(progress.current(state.load())[2])
        self.assertEqual(names, ["Stardust", "Comet", "Planet", "Star"])
        self.assertEqual(state.load()["looks"], {})                        # back to the latest: no pin left
        self.assertEqual(progress.current(state.load())[1], 3)             # actions never went back

    def test_one_form_only(self):
        from bashou.board import Board
        with state.locked() as s:
            s["starter"] = "star"
        board = Board()
        board.pos = 0
        board.key("form")
        self.assertIn("Only one form", board.message)


if __name__ == "__main__":
    unittest.main()
