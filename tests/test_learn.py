import contextlib
import io
import re
import tempfile
import unittest
from pathlib import Path

from bashou import achievements, dialogue, learn, state


class LearnTest(unittest.TestCase):
    def test_every_hint_example_is_explained(self):
        """`bashou learn` must know every command and option the pets suggest."""
        for achievement, example in ((a.id, a.example) for a in achievements.ALL if a.example):
            for piece, meaning in learn.explain(example):
                self.assertNotIn("no notes", meaning, f"{example}: {piece}")
                self.assertNotIn("an option of", meaning, f"{example}: {piece}")

    def test_pieces_keep_quotes_values_and_operators_together(self):
        pieces = dict(learn.explain("grep -E 'cat|dog' f | tar -czf out.tgz d 2>&1 > log"))
        self.assertIn("cat|dog", pieces)                   # a quoted pattern isn't a pipe
        self.assertIn("-czf out.tgz", pieces)              # the value goes with its option
        self.assertIn("2>&1", pieces)
        self.assertEqual(pieces["log"], "the file")

    def test_network_commands(self):
        pieces = dict(learn.explain("ip route get 192.0.2.10; ss -tn state established; tcpdump -nn -r cap.pcap"))
        self.assertIn("nothing is sent", pieces["get"])
        self.assertIn("open connections", pieces["established"])
        self.assertIn("capture file", pieces["-r cap.pcap"])
        self.assertNotIn("man", pieces["-tn"])

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
                text = re.sub(r"\x1b\[[0-9;]*m", "", out.getvalue())
                self.assertIn("du -sh *", text)
                self.assertIn("human sizes", text)
            finally:
                state.CACHE = old


class LearnDisplayTest(unittest.TestCase):
    """Owner, 2026-09-26: the old flat grey list didn't make anyone want to read it."""

    def plain(self, command):
        return re.sub(r"\x1b\[[0-9;]*m", "", learn.render(command, width=100))

    def test_the_command_is_shown_as_typed(self):
        for command in ('find . -name "*.py" -exec grep -l TODO {} \\;', "grep -E 'a|b' f 2>&1 > log",
                        'for f in *.log; do gzip "$f"; done'):
            self.assertEqual(self.plain(command).split("\n")[1], "  " + command)

    def test_one_line_per_flag_and_numbered_steps(self):
        text = self.plain("tar -czf backup.tgz ~/docs | grep -v log")
        self.assertRegex(text, r"\n +-c +create an archive")
        self.assertRegex(text, r"\n +-f backup.tgz +the archive file")
        self.assertIn("1. tar", text)
        self.assertIn("2. grep", text)
        self.assertNotIn("1. du", self.plain("du -sh *"))           # one command: no number

    def test_flags_after_find_exec_belong_to_the_command_it_runs(self):
        rows = learn.pieces('find . -exec grep -l TODO {} \\;')
        self.assertIn("only the names", dict((r[0], r[1]) for r in rows)["-l"])
        self.assertIn("-exec", rows[-1][1])


if __name__ == "__main__":
    unittest.main()
