import contextlib
import io
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bashou import cli, creatures, pony, progress, state
from tests.test_regressions import TempState

ROOT = Path(__file__).resolve().parent.parent


def out(fn, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fn(*args)
    return code, buf.getvalue()


class HidingPlacesTest(unittest.TestCase):
    """Each pony's word is where the owner hid it (2026-10-09), and only there."""

    def word(self, text):
        return re.search(r"bashou pony (\w+)", text).group(1)

    def test_each_hiding_place_brings_its_pony(self):
        places = {
            "pony_explorer": (ROOT / "doc/easter_egg").read_text(),
            "pony_package": re.search(r'^SUMMARY = "(.*)"', (ROOT / "tools/package.py").read_text(), re.M).group(1),
            "pony_web": re.search(r"<!--(.*?)-->", (ROOT / "doc/install.html").read_text()).group(1),
        }
        fr = re.search(r"<!--(.*?)-->", (ROOT / "doc/install.fr.html").read_text()).group(1)
        self.assertEqual(self.word(fr), self.word(places["pony_web"]))
        for want, text in places.items():
            with self.subTest(want):
                self.assertEqual(pony.PONIES[pony.digest(self.word(text))], want)

    def test_the_package_summary_stays_short(self):
        """Debian's lintian warns past 80 characters; `apt search` shows the summary on one line."""
        summary = re.search(r'^SUMMARY = "(.*)"', (ROOT / "tools/package.py").read_text(), re.M).group(1)
        self.assertLessEqual(len(summary), 80)

    def test_every_pony_has_a_way_in(self):
        reachable = {pony.FOAL, *pony.PONIES.values()}
        self.assertEqual(reachable, set(pony.herd()))
        self.assertEqual(len(pony.herd()), 11)
        self.assertEqual({p for p, _, _ in pony.JOKES} - set(pony.PONIES.values()), set())
        self.assertEqual(set(pony.where()), set(pony.herd()))
        self.assertEqual(set(pony.peeks()), {p for p, _, _ in pony.JOKES})

    def test_no_word_in_plain_text_in_the_code(self):
        """Reading bashou/ spoils nothing: the words are hashes, and rot13 for the jokes' hints."""
        words = ["hoof", "trail", "hay", "mane", "envy", "cud", "hug", "shh", "crumb", "esc"]
        for word in words:
            self.assertIn(pony.digest(word), pony.PONIES, word)
        code = (ROOT / "bashou/pony.py").read_text()
        for word in words:
            self.assertNotRegex(code, rf"\bbashou pony {word}\b|[\"']{word}[\"']", word)


class HelpTest(unittest.TestCase):
    def test_only_dash_dash_help_shows_the_pony(self):
        _code, plain = out(cli.print_help)
        _code, dashed = out(cli.print_help, True)
        self.assertNotIn("bashou pony", plain)
        self.assertIn("bashou pony", dashed)

    def test_the_parser_help_is_the_dash_dash_help(self):
        for flag in ("--help", "-h"):
            buf = io.StringIO()
            with mock.patch("sys.argv", ["bashou", flag]), contextlib.redirect_stdout(buf), \
                    self.assertRaises(SystemExit):
                cli.main()
            self.assertIn("bashou pony", buf.getvalue(), flag)

    def test_pony_is_a_hidden_command(self):
        command = next(c for c in cli.COMMANDS if c.name == "pony")
        self.assertTrue(command.hidden)
        bash = (ROOT / "bashou.bash").read_text()
        self.assertNotRegex(re.search(r'_bashou_commands="(.*)"', bash).group(1), r"\bpony\b")


class ClaimTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        data = Path(self.tmp.name)
        self.patches = [mock.patch.object(state, "DATA", data), mock.patch.object(state, "STATE", data / "state.json")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_bashou_pony_alone_brings_the_foal_once(self):
        code, first = out(pony.main, None)
        self.assertEqual(code, 0)
        self.assertIn("New pet", first)
        s = state.load()
        self.assertEqual(s["ponies"], ["pony_foal"])
        self.assertIn("pony_foal", s["pets"])
        _code, again = out(pony.main, None)
        self.assertNotIn("New pet", again)
        self.assertIn("already in your herd", again)
        self.assertEqual(state.load()["pets"].count("pony_foal"), 1)

    def test_a_word_brings_its_pony_and_any_case_works(self):
        _code, text = out(pony.main, "  CRUMB ")
        self.assertIn("Chef pony", text)
        self.assertIn("pony_chef", state.load()["pets"])

    def test_an_unknown_word_brings_nothing(self):
        code, text = out(pony.main, "unicorn")
        self.assertEqual(code, 1)
        self.assertIn("No pony answers", text)
        self.assertEqual(state.load()["ponies"], [])

    def test_ponies_stay_secret_until_claimed(self):
        s = state.load()
        shown = [pet for pet, _ in creatures.roster(s)]
        self.assertFalse(set(pony.herd()) & set(shown))
        out(pony.main, "esc")
        shown = [pet for pet, _ in creatures.roster(state.load())]
        self.assertEqual(set(pony.herd()) & set(shown), {"pony_vim"})

    def test_bashou_pets_lists_the_herd_together(self):
        out(pony.main, None)
        out(pony.main, "hug")
        _code, text = out(cli.pets)
        self.assertIn("Ponies", text)
        self.assertIn("2/11", text)
        self.assertLess(text.index("Ponies"), text.index("Foal"))

    def test_a_save_without_ponies_loads(self):
        """Saves from before 0.8.4 have no "ponies"."""
        s = state.default()
        del s["ponies"]
        state.STATE.write_text(__import__("json").dumps(s))
        self.assertEqual(state.load()["ponies"], [])


class PeekTest(unittest.TestCase):
    def peek(self, line, ponies=()):
        return pony.peek({"ponies": list(ponies)}, line)

    def test_each_joke_shows_its_word(self):
        for line, word in (("cowsay hello", "envy"), ("fortune | cowsay", "envy"), ("apt moo", "cud"),
                           ("apt-get moo", "cud"), ("make love", "hug"), ("man woman", "shh"),
                           ("sudo make me a sandwich", "crumb"), (":wq", "esc"), (":q!", "esc"), ("  :x ", "esc")):
            with self.subTest(line):
                said = self.peek(line)
                self.assertIsNotNone(said)
                self.assertIn(f"bashou pony {word}", said)
                self.assertEqual(pony.PONIES[pony.digest(word)], next(p for p, rx, _ in pony.JOKES if rx.search(line)))

    def test_near_misses_show_nothing(self):
        for line in ("make lovely", "make love-letter", "man women", "man woman-ish", "make me a sandwich",
                     "echo :wq", "vim :wq", "apt moon", "mycowsay", "git commit -m 'apt moo'"):
            with self.subTest(line):
                self.assertIsNone(self.peek(line))

    def test_a_claimed_pony_doesnt_peek_again(self):
        self.assertIsNone(self.peek("cowsay hi", ["pony_jealous"]))
        self.assertIsNotNone(self.peek("apt moo", ["pony_jealous"]))

    def test_the_pet_sees_failed_and_unknown_commands(self):
        """`:wq` is "command not found" (127) and `make love` fails: both must still reach the peek."""
        s = state.default()
        s["starter"] = "star"
        for status, line in ((127, ":wq"), (2, "make love")):
            progress.record(s, status, line, "2026-10-10", 12)
            self.assertIsNotNone(pony.peek(s, line))


class CompanionPeekTest(TempState):
    """The pet itself sees the joke in the terminal and says the word, even for a failed command."""

    def test_a_joke_typed_in_the_terminal_brings_the_peek(self):
        import os
        from bashou.companion import Companion
        pet = Companion(os.getpid())
        pet.events = state.DATA / "events.test"
        for n, (status, line, word) in enumerate(((127, ":wq", "esc"), (2, "make love", "hug"))):
            pet.notes = []
            with open(pet.events, "a") as f:
                f.write(f"{status}\t    {n}  {line}\n")
            pet.read_events()
            self.assertIn(f"bashou pony {word}", pet.notes[0])


if __name__ == "__main__":
    unittest.main()
