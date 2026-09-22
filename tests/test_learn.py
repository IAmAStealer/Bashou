import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from bashou import dialogue, learn, state


class LearnTest(unittest.TestCase):
    def test_every_hint_example_is_explained(self):
        """`bashou learn` must know every command and option the pets suggest."""
        for achievement, example in dialogue.EXAMPLES.items():
            for piece, meaning in learn.explain(example):
                self.assertNotIn("no notes", meaning, f"{example}: {piece}")
                self.assertNotIn("an option of", meaning, f"{example}: {piece}")

    def test_pieces_keep_quotes_values_and_operators_together(self):
        pieces = dict(learn.explain("grep -E 'cat|dog' f | tar -czf out.tgz d 2>&1 > log"))
        self.assertIn("cat|dog", pieces)                   # a quoted pattern isn't a pipe
        self.assertIn("-czf out.tgz", pieces)              # the value goes with its option
        self.assertIn("2>&1", pieces)
        self.assertEqual(pieces["log"], "the file")

    def test_unknown_commands_point_to_man(self):
        self.assertIn("man frobnicate", learn.explain("frobnicate --x")[0][1])

    def test_explains_what_the_pet_last_suggested(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, state.CACHE = state.CACHE, Path(tmp)
            try:
                learn.remember("*sniff* Try `du -sh *` (achv: Sizer)")
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    self.assertEqual(learn.main([]), 0)
                self.assertIn("du -sh *", out.getvalue())
                self.assertIn("human sizes", out.getvalue())
            finally:
                state.CACHE = old


if __name__ == "__main__":
    unittest.main()
