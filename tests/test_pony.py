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
        forms = [re.search(r"<!--(.*?)-->", (ROOT / ".github/ISSUE_TEMPLATE" / name).read_text()).group(1)
                 for name in ("1-bug.yml", "6-bug-fr.yml")]
        self.assertEqual(self.word(forms[0]), self.word(forms[1]))
        places["pony_form"] = forms[0]
        for want, text in places.items():
            with self.subTest(want):
                self.assertEqual(pony.PONIES[pony.digest(self.word(text))], want)

    def test_the_package_summary_stays_short(self):
        """Debian's lintian warns past 80 characters; `apt search` shows the summary on one line."""
        summary = re.search(r'^SUMMARY = "(.*)"', (ROOT / "tools/package.py").read_text(), re.M).group(1)
        self.assertLessEqual(len(summary), 80)

    def test_every_pony_has_a_way_in(self):
        jokes = {p for p, _rx in pony.JOKES}
        self.assertEqual({pony.FOAL, *pony.PONIES.values()} | jokes, set(pony.herd()))
        self.assertEqual(len(pony.herd()), 13)
        self.assertFalse(jokes & set(pony.PONIES.values()), "a joke brings its pony by itself: no word")
        self.assertEqual(set(pony.where()), {pony.FOAL, *pony.PONIES.values()})
        self.assertEqual(set(pony.arrivals()), jokes)
        self.assertEqual(set(pony.hints()), {*pony.PONIES.values(), "jokes"})

    def test_no_word_outside_its_hiding_place(self):
        """Owner, 2026-10-10: only the hiding place gives the word. Not the code (hashes), not a hint,
        not the pet's lines."""
        from bashou import i18n
        words = ["hoof", "trail", "hay", "mane", "sleuth", "quill"]
        for word in words:
            self.assertIn(pony.digest(word), pony.PONIES, word)
        texts = [(ROOT / "bashou/pony.py").read_text()]
        for lang in ("en", "fr"):
            i18n.use(lang)
            texts += [*pony.hints().values(), *pony.arrivals().values(), *pony.where().values()]
        i18n.use(None)
        for f in creatures.FAMILIES.values():
            if f.herd:
                texts += f.tips + f.personal
        for word in words:
            for text in texts:
                self.assertNotRegex(text, rf"bashou pony {word}\b|[\"']{word}[\"']", word)


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
        _code, text = out(pony.main, "  TRAIL ")
        self.assertIn("Explorer pony", text)
        self.assertIn("pony_explorer", state.load()["pets"])

    def test_an_unknown_word_brings_nothing(self):
        code, text = out(pony.main, "unicorn")
        self.assertEqual(code, 1)
        self.assertIn("No pony answers", text)
        self.assertEqual(state.load()["ponies"], [])

    def test_ponies_stay_secret_until_claimed(self):
        s = state.load()
        shown = [pet for pet, _ in creatures.roster(s)]
        self.assertFalse(set(pony.herd()) & set(shown))
        out(pony.main, "hay")
        shown = [pet for pet, _ in creatures.roster(state.load())]
        self.assertEqual(set(pony.herd()) & set(shown), {"pony_package"})

    def test_bashou_pets_lists_the_herd_together(self):
        out(pony.main, None)
        out(pony.main, "mane")
        _code, text = out(cli.pets)
        self.assertIn("Ponies", text)
        self.assertIn("2/13", text)
        self.assertLess(text.index("Ponies"), text.index("Foal"))

    def test_a_save_without_ponies_loads(self):
        """Saves from before 0.8.4 have no "ponies"."""
        s = state.default()
        del s["ponies"]
        state.STATE.write_text(__import__("json").dumps(s))
        self.assertEqual(state.load()["ponies"], [])


class JokeTest(unittest.TestCase):
    def joke(self, line, ponies=()):
        s = state.default()
        s["starter"], s["ponies"] = "star", list(ponies)
        return s, pony.joke(s, line)

    def test_each_joke_brings_its_pony_at_once(self):
        """Owner, 2026-10-10: the pet saw the joke, no word to type."""
        for line, want in (("cowsay hello", "pony_jealous"), ("fortune | cowsay", "pony_jealous"),
                           ("apt moo", "pony_moo"), ("apt-get moo", "pony_moo"), ("make love", "pony_heart"),
                           ("man woman", "pony_library"), ("sudo make me a sandwich", "pony_chef"),
                           (":wq", "pony_vim"), (":q!", "pony_vim"), ("  :x ", "pony_vim")):
            with self.subTest(line):
                s, said = self.joke(line)
                self.assertEqual(s["ponies"], [want])
                self.assertIn(want, s["pets"])
                self.assertIn("joins your herd", said[0])
                self.assertNotIn("bashou pony", said[0])

    def test_near_misses_bring_nothing(self):
        for line in ("make lovely", "make love-letter", "man women", "man woman-ish", "make me a sandwich",
                     "echo :wq", "vim :wq", "apt moon", "mycowsay", "git commit -m 'apt moo'"):
            with self.subTest(line):
                s, said = self.joke(line)
                self.assertEqual((said, s["ponies"]), ([], []))

    def test_a_pony_comes_once(self):
        s, said = self.joke("cowsay hi", ["pony_jealous"])
        self.assertEqual((said, s["ponies"]), ([], ["pony_jealous"]))


class HintTest(unittest.TestCase):
    def test_hints_lead_through_the_hiding_places_then_the_jokes(self):
        s = {"ponies": [pony.FOAL]}
        seen = []
        for p in [*(k for k in pony.hints() if k != "jokes"), *(p for p, _rx in pony.JOKES)]:
            text = pony.hint(s)
            if text not in seen:
                seen.append(text)
            s["ponies"].append(p)
        self.assertEqual(seen, list(pony.hints().values()))
        self.assertIsNone(pony.hint(s))

    def test_bashou_pony_gives_a_hint_but_no_word(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(state, "DATA", Path(tmp)), \
                mock.patch.object(state, "STATE", Path(tmp) / "state.json"):
            _code, text = out(pony.main, None)
        self.assertIn(pony.hints()["pony_explorer"][:30], text)
        self.assertNotIn("bashou pony trail", text)


class CompanionJokeTest(TempState):
    """The pet itself sees the joke in the terminal, even when the command failed."""

    def test_a_joke_typed_in_the_terminal_brings_the_pony(self):
        import os
        from bashou.companion import Companion
        pet = Companion(os.getpid())
        pet.events = state.DATA / "events.test"
        for n, (status, line, want) in enumerate(((127, ":wq", "pony_vim"), (2, "make love", "pony_heart"))):
            pet.notes = []
            with open(pet.events, "a") as f:
                f.write(f"{status}\t    {n}  {line}\n")
            pet.read_events()
            self.assertIn("joins your herd", pet.notes[0])
            self.assertIn(want, state.load()["pets"])

if __name__ == "__main__":
    unittest.main()
