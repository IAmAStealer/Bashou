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

    def test_mouse_reports_are_one_key_each(self):
        """Owner, 2026-10-16: click and hover in bashou swap. SGR reports (ESC [ < b ; x ; y M) stay whole."""
        keys = terminal.split_keys("\x1b[<0;10;5M\x1b[<0;10;5m\x1b[<35;11;6M\x1b[<64;1;1M\x1b[<65;1;1Mq\x1b[<3")
        self.assertEqual([terminal.mouse(k) for k in keys],
                         [("click", 10, 5), None, ("move", 11, 6), ("wheel_up", 1, 1), ("wheel_down", 1, 1), None])
        self.assertEqual(terminal.name(keys[-1]), "quit")                         # a cut report is dropped
        self.assertIsNone(terminal.mouse("\x1b[A"))

    def test_the_mouse_is_only_asked_for_by_screens_that_use_it(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), terminal.Screen(fd=self.slave):
            pass
        self.assertNotIn("?1000h", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out), terminal.Screen(fd=self.slave, mouse=True):
            pass
        self.assertIn("?1006h", out.getvalue())
        self.assertIn("?1000l", out.getvalue())                                   # given back on the way out

    def test_paused_gives_the_terminal_back(self):
        before = modes(self.slave)
        with contextlib.redirect_stdout(io.StringIO()), terminal.Screen(fd=self.slave) as screen:
            with screen.paused():
                self.assertEqual(modes(self.slave), before)
            self.assertNotEqual(modes(self.slave), before)


if __name__ == "__main__":
    unittest.main()
