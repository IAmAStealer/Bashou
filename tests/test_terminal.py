import contextlib
import io
import os
import pty
import termios
import unittest

from bashou import terminal


def modes(fd):
    """The terminal's settings, without PENDIN: macOS sets that flag itself when the line mode comes back
    (input to retype), it isn't one we set."""
    attrs = termios.tcgetattr(fd)
    attrs[3] &= ~getattr(termios, "PENDIN", 0)
    return attrs


class ScreenTest(unittest.TestCase):
    def setUp(self):
        self.master, self.slave = pty.openpty()
        self.addCleanup(os.close, self.master)
        self.addCleanup(os.close, self.slave)

    def test_the_terminal_comes_back_even_after_a_crash(self):
        before = modes(self.slave)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(ZeroDivisionError):
            with terminal.Screen(fd=self.slave):
                self.assertNotEqual(modes(self.slave), before)     # keys without Enter
                1 / 0
        self.assertEqual(modes(self.slave), before)
        self.assertTrue(out.getvalue().endswith("\x1b[?1049l"))              # back from the alternate screen
        self.assertIn("\x1b[?25h", out.getvalue())                          # the cursor shows again

    def test_keys_arrive_one_by_one(self):
        with contextlib.redirect_stdout(io.StringIO()), terminal.Screen(fd=self.slave) as screen:
            self.assertEqual(screen.keys(0.01), [])
            os.write(self.master, b"\x1b[Aq")
            keys = screen.keys(1)
        self.assertEqual(keys, ["\x1b[A", "q"])
        self.assertEqual([terminal.name(k) for k in keys], ["up", "quit"])
        self.assertEqual(terminal.name("f", {"f": "form"}), "form")

    def test_paused_gives_the_terminal_back(self):
        before = modes(self.slave)
        with contextlib.redirect_stdout(io.StringIO()), terminal.Screen(fd=self.slave) as screen:
            with screen.paused():
                self.assertEqual(modes(self.slave), before)
            self.assertNotEqual(modes(self.slave), before)


if __name__ == "__main__":
    unittest.main()
