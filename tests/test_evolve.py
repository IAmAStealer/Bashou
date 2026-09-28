import contextlib
import io
import unittest
from unittest import mock

from bashou import achievements, creatures, evolve, progress, render, state
from tests.test_regressions import TempState


def evolving_stardust():
    s = state.default()
    s["starter"], s["achievements"] = "star", [f"a{i}" for i in range(9)]
    progress.check(s, achievements.ALL[:1])                              # the 10th: level 3, the Meteor
    return s


def shape(sprite, stage):
    """The pixels a form draws, colors aside: an evolution must change more than the colors."""
    return render.grid(creatures.get(sprite), [], stage)


# Forms that only change color, until they're redrawn. User report: "it says it's evolving, yet nothing
# evolves" (the Crystal golem's last evolution, at level 20).
RECOLORS = {("crystal", "jade_golem")}


class EveryPetEvolvesTest(unittest.TestCase):
    """Every pet and starter line, from the lists: a new pet is checked without touching this test."""

    def queued(self, s, who):
        return [e for e in s["evolving"] if e["who"] == who]

    def walk(self, who, forms, s, steps):
        """Run each step (it earns something), watch every evolution it queues. Returns the forms reached."""
        reached = [progress.reached(s, who)]
        for step in steps:
            notes = step()
            evolving = [n for n in notes if "is evolving" in n]
            for e in self.queued(s, who):
                self.assertGreater(e["to"], e["from"], (who, e))
                pair = (forms[e["from"] - 1], forms[e["to"] - 1])
                if pair not in RECOLORS:
                    self.assertTrue(shape(pair[0], e["from"]) != shape(pair[1], e["to"]), f"{who}: {pair} only changes color")
                self.assertTrue(evolving, (who, e))                     # a queued evolution is announced
                progress.watched(s, who)
                self.assertEqual(progress.current(s, who)[0], pair[1])  # and shown once watched
            reached.append(progress.reached(s, who))
        self.assertEqual(reached, sorted(reached), who)                 # never goes back
        return reached

    @mock.patch("bashou.which.installed", return_value=True)
    def test_every_pet(self, _):
        for pet in creatures.NAMES:
            with self.subTest(pet=pet):
                s = state.default()
                s["starter"], s["pets"] = "star", [pet]
                if pet in progress.COMMAND_LADDER:                       # the Slime: your command count
                    def step(n):
                        s["commands"] = n
                        return progress.check(s)
                    steps = [lambda n=n: step(n) for n in progress.COMMAND_LADDER[pet]]
                else:                                                   # the others: their achievements
                    steps = [lambda a=a: progress.check(s, [a]) for a in achievements.family(pet)]
                reached = self.walk(pet, creatures.forms(pet), s, steps)
                if creatures.can_evolve(pet):
                    self.assertTrue(steps, f"{pet} has forms but nothing makes it evolve")
                    self.assertEqual(reached[-1], len(creatures.forms(pet)), pet)   # all earned: the last form
                else:
                    self.assertEqual(set(reached), {1}, pet)

    def test_every_starter_line(self):
        needed = progress.ACHIEVEMENTS_PER_LEVEL * (progress.MAX_LEVEL - 1)
        ids = [achievements.A(f"test{i}", "cat", "", "") for i in range(needed)]
        for line, forms in creatures.STARTERS.items():
            with self.subTest(line=line):
                s = state.default()
                s["starter"] = line
                reached = self.walk("starter", forms, s, [lambda a=a: progress.check(s, [a]) for a in ids])
                self.assertEqual(reached[-1], len(forms))

    def test_recolors_are_still_recolors(self):
        """Once one is redrawn, take it out of RECOLORS so the check covers it again."""
        for old, new in RECOLORS:
            self.assertEqual(shape(old, 1), shape(new, 1), (old, new))


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
        self.assertIn("Meteor", shown[-1][2])

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
        self.assertEqual((s["evolving"], progress.current(s)[2]), ([], "Meteor"))

    def test_nothing_waiting(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(evolve.main(), 0)


class FormSwitchTest(TempState):
    def test_f_cycles_the_forms_reached(self):
        from bashou.board import Board
        with state.locked() as s:
            s["starter"], s["achievements"] = "star", [f"a{i}" for i in range(95)]
        board = Board()
        board.pos = 0
        names = []
        for _ in range(7):
            board.key("form")
            names.append(progress.current(state.load())[2])
        self.assertEqual(names, ["Stardust", "Meteor", "Comet", "Moon", "Planet", "Star", "Red giant"])
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


class NoSpoilerTest(unittest.TestCase):
    """Forms are to discover (owner): only the ones reached are named, then "?" and its level."""

    def test_the_board_names_only_reached_forms(self):
        from bashou.board import ladder_line
        s = state.default()
        s["starter"], s["achievements"] = "star", [f"a{i}" for i in range(15)]
        self.assertEqual(ladder_line(s), "Stardust → Meteor → ? (level 5)")
        s["achievements"] = [f"a{i}" for i in range(99)]
        self.assertEqual(ladder_line(s), "Stardust → Meteor → Comet → Moon → Planet → Star → Red giant")

    def test_the_starter_choice_names_only_the_first_form(self):
        from bashou import starter
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            starter.draw(0, False)
        import re
        from bashou import creatures
        text = out.getvalue() + " ".join(creatures.STARTER_BLURBS.values())
        for forms in creatures.STARTERS.values():
            for later in forms[1:]:
                self.assertIsNone(re.search(rf"\b{creatures.FORM_NAMES[later]}\b", text, re.I), later)


if __name__ == "__main__":
    unittest.main()
