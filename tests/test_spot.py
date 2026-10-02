import base64
import datetime
import ipaddress
import json
import random
import re
import unittest
import urllib.parse

from bashou import creatures, progress, spot, state
from bashou.spot import screen


# Validation regexes from the web (2026-10-03): IPv4 and IPv6 from ditig.com
# (https://www.ditig.com/validating-ipv4-and-ipv6-addresses-with-regexp), MAC and UUID v4 from
# dev-toolbox.tech; base64 per RFC 4648 (groups of 4, = padding only at the end).
IPV4 = r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$"
IPV6 = (r"^((?:[0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4}|(?:[0-9A-Fa-f]{1,4}:){1,7}:|:(?::[0-9A-Fa-f]{1,4}){1,7}|"
        r"(?:[0-9A-Fa-f]{1,4}:){1,6}:[0-9A-Fa-f]{1,4}|(?:[0-9A-Fa-f]{1,4}:){1,5}(?::[0-9A-Fa-f]{1,4}){1,2}|"
        r"(?:[0-9A-Fa-f]{1,4}:){1,4}(?::[0-9A-Fa-f]{1,4}){1,3}|(?:[0-9A-Fa-f]{1,4}:){1,3}(?::[0-9A-Fa-f]{1,4}){1,4}|"
        r"(?:[0-9A-Fa-f]{1,4}:){1,2}(?::[0-9A-Fa-f]{1,4}){1,5}|[0-9A-Fa-f]{1,4}:(?:(?::[0-9A-Fa-f]{1,4}){1,6})|"
        r":(?:(?::[0-9A-Fa-f]{1,4}){1,6}))$")
MAC = r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
UUID4 = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
BASE64 = r"^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$"
BASE64URL = r"^[A-Za-z0-9_-]+$"


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class KindsTest(unittest.TestCase):
    """Owner: 20 kinds of strings seen in IT, generated at random (never the same twice)."""

    def test_twenty_kinds_each_generated_right(self):
        self.assertEqual(len(spot.KINDS), 21)
        rng = random.Random(1)
        def ipv6(t):
            self.assertRegex(t, IPV6)
            self.assertEqual(str(ipaddress.IPv6Address(t)), t)                 # canonical: RFC 5952
            self.assertTrue(t.startswith("fe80::") or ipaddress.IPv6Address(t) in ipaddress.IPv6Network("2000::/3"))

        def jwt(t):
            parts = t.split(".")
            self.assertEqual(len(parts), 3)
            for part in parts:
                self.assertRegex(part, BASE64URL)                                # base64url, no padding
            head = json.loads(base64.urlsafe_b64decode(parts[0] + "=" * (-len(parts[0]) % 4)))
            self.assertIn("alg", head)

        checks = {
            "ipv4": lambda t: (self.assertRegex(t, IPV4), self.assertEqual(str(ipaddress.IPv4Address(t)), t)),
            "ipv6": ipv6,
            "mac": lambda t: self.assertRegex(t, MAC),
            "uuid": lambda t: self.assertRegex(t, UUID4),
            "base64": lambda t: (self.assertRegex(t, BASE64), base64.b64decode(t, validate=True).decode()),
            "hex": lambda t: self.assertRegex(t, r"^(0x[0-9a-f]+|[0-9a-f]{2}( [0-9a-f]{2})*)$"),
            "md5": lambda t: self.assertRegex(t, r"^[0-9a-f]{32}$"),
            "sha1": lambda t: self.assertRegex(t, r"^[0-9a-f]{40}$"),
            "encrypted": lambda t: (self.assertRegex(t, BASE64), self.assertTrue(t.startswith("U2FsdGVkX1"))),
            "jwt": jwt,
            "basic": lambda t: (self.assertRegex(t, r"^Basic " + BASE64[1:]),
                                self.assertRegex(base64.b64decode(t[6:]).decode(), r"^[^:]+:.+$")),
            "email": lambda t: self.assertRegex(t, r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"),
            "url": lambda t: self.assertTrue(urllib.parse.urlparse(t).scheme in ("http", "https")
                                             and urllib.parse.urlparse(t).netloc),
            "regex": re.compile,
            "date": lambda t: datetime.datetime.fromisoformat(t.replace("Z", "+00:00")),
            "timestamp": lambda t: self.assertTrue(2014 <= datetime.datetime.fromtimestamp(int(t)).year <= 2031),
        }
        for kind, (label, family, make) in spot.KINDS.items():
            for _ in range(500):
                text = make(rng)
                self.assertTrue(text and len(text) <= spot.LONGEST, (kind, text))   # fits between the answers
                if kind in checks:
                    checks[kind](text)

    def test_labels_are_short_in_every_language(self):
        from bashou import i18n
        for lang in i18n.LANGUAGES:
            cat = i18n.catalog(lang) if lang != "en" else {}
            for label, family, make in spot.KINDS.values():
                self.assertLessEqual(len(cat.get(label) or label), spot.LABEL, (lang, label))

    def test_answers_are_four_different_with_the_right_one(self):
        rng = random.Random(2)
        for kind in spot.KINDS:
            for _ in range(20):
                answers = spot.choices(kind, rng)
                self.assertEqual(len(set(answers)), 4)
                self.assertIn(kind, answers)
        near = spot.choices("md5", rng)                                       # wrong answers look alike
        self.assertTrue(all(spot.KINDS[k][1] == "code" for k in near))


class GameTest(unittest.TestCase):
    def game(self):
        self.clock = Clock()
        return spot.Game(random.Random(3), self.clock)

    def right(self, g):
        return spot.ARROWS[g.answers.index(g.kind)]

    def wrong(self, g):
        return next(a for a, k in zip(spot.ARROWS, g.answers) if k != g.kind)

    def test_the_bag_holds_every_kind_twice(self):
        g = self.game()
        self.assertEqual(len(g.bag) + 1, 2 * len(spot.KINDS))
        self.assertEqual(sorted(g.bag + [g.kind]), sorted(list(spot.KINDS) * 2))

    def test_a_good_answer_takes_it_out_a_wrong_one_puts_it_back(self):
        g = self.game()
        size = len(g.bag)
        g.answer(self.right(g))
        self.assertEqual((g.score, g.mistakes, len(g.bag)), (1, 0, size - 1))
        kind = g.kind
        g.answer(self.wrong(g))
        self.assertEqual((g.score, g.mistakes, len(g.bag)), (1, 1, size - 1))   # one out, the same one back in
        self.assertEqual(g.last, (False, kind))
        self.assertIn(kind, g.bag + [g.kind])

    def test_25_seconds_for_the_whole_game(self):
        g = self.game()
        self.clock.now = spot.GAME_SECONDS - 0.1
        self.assertFalse(g.over())
        g.answer(self.right(g))
        self.clock.now = spot.GAME_SECONDS
        self.assertTrue(g.over())
        g.answer(self.right(g))                                               # too late: not counted
        self.assertEqual(g.score, 1)

    def test_an_empty_bag_ends_the_game(self):
        g = self.game()
        for _ in range(2 * len(spot.KINDS)):
            g.answer(self.right(g))
        self.assertEqual(g.score, 2 * len(spot.KINDS))
        self.assertTrue(g.over())

    def test_other_keys_do_nothing(self):
        g = self.game()
        kind = g.kind
        g.answer("enter")
        self.assertEqual((g.kind, g.score, g.mistakes), (kind, 0, 0))

    def test_r_restarts_and_q_quits_in_the_middle_of_a_game(self):
        """Owner: r starts a new game at once (the one going on doesn't count)."""
        import contextlib
        import io

        class Keys:
            def __init__(self, *keys):
                self.left = list(keys)

            def keys(self, timeout):
                return [self.left.pop(0)] if self.left else []

        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(screen.play(Keys("\x1b[A", "r"), 80, 14), "restart")
            self.assertIsNone(screen.play(Keys("q"), 80, 14))

    def test_tiers(self):
        self.assertEqual(spot.tier(4), "")
        self.assertEqual(spot.tier(10), "Sharp eyes")
        self.assertEqual(spot.tier(20), "Eagle eyes")                             # the last one: 20
        self.assertEqual(spot.GAME_SECONDS, 25)

    def test_the_string_in_the_middle_the_answers_around_the_clock_on_top(self):
        """Owner: the string right in the middle, little distraction, the time at the top of the terminal,
        the answers around the string with room around them."""
        for cols, rows in ((80, 14), (160, 48), (100, 30)):
            g = self.game()
            for _ in range(80):
                parts = screen.layout(g, cols, rows)
                for r, c, text, style in parts:
                    self.assertTrue(1 <= r <= rows and c >= 1 and c + len(text) - 1 <= cols, (cols, rows, text))
                mid = rows // 2 + 1
                row_of = {text: (r, c) for r, c, text, style in parts}
                r, c = row_of[g.text]
                self.assertEqual(r, mid)
                self.assertLessEqual(abs((c + len(g.text) / 2) - (cols / 2 + 1)), 1)        # centered
                on_mid = sorted((c, c + len(t) - 1) for r, c, t, st in parts if r == mid)
                for (a, b), (x, y) in zip(on_mid, on_mid[1:]):
                    self.assertEqual(x - b - 1, spot.GAP, (cols, on_mid))                    # room, but close
                if g.last:                                                                   # ✔/✗ above the top answer
                    self.assertEqual(row_of["✔" if g.last[0] else "✗"], (mid - 5, cols // 2 + 1))
                rows_used = sorted({r for r, c, t, st in parts if t})
                self.assertEqual(rows_used[0], 1)                                            # the clock on top
                self.assertTrue(all(abs(r - mid) >= 3 for r in rows_used if r not in (1, rows, mid)))
                g.answer(random.choice(spot.ARROWS))
                if g.over():
                    g = self.game()

    def test_the_end_screen_fits(self):
        g = self.game()
        for line in screen.end_screen(g, 5, 80, 14).split("\n"):
            self.assertLessEqual(screen.visible_len(line.replace("\x1b[H\x1b[2J", "")), 80)

class RewardTest(unittest.TestCase):
    """Owner, 2026-10-03: 11 good answers and no new pet, no achievement (the prototype had none)."""

    def test_a_best_score_saved_before_brings_the_chameleon(self):
        s = state.read('{"language": "en", "starter": "star", "spot": {"best": 11, "games": 3}}')
        notes = progress.check(s)
        self.assertIn("chameleon", s["pets"])
        self.assertLessEqual({"first_glance", "quick_eye", "sharp_eyes"}, set(s["achievements"]))
        self.assertNotIn("hawk_eyes", s["achievements"])
        self.assertEqual(creatures.form("chameleon", progress.reached(s, "chameleon")), "mantis")
        self.assertTrue(any("Chameleon" in n for n in notes), notes)

    def test_the_eagle_needs_every_achievement(self):
        s = state.default()
        s["spot"] = {"best": 20, "games": 10, "kinds": list(spot.KINDS), "clean": 10}
        progress.check(s)
        self.assertEqual(creatures.form("chameleon", progress.reached(s, "chameleon")), "eagle")
        self.assertEqual(len(creatures.FORMS["chameleon"]), 5)

    def test_a_game_is_saved_with_its_kinds_and_announces_achievements(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(state, "DATA", Path(tmp)), \
                mock.patch.object(state, "STATE", Path(tmp) / "state.json"):
            clock = Clock()
            g = spot.Game(random.Random(4), clock)
            for _ in range(6):
                g.answer(spot.ARROWS[g.answers.index(g.kind)])
            before, notes = screen.save(g)
            saved = state.load()["spot"]
            self.assertEqual((before, saved["best"], saved["games"], saved["clean"]), (0, 6, 1, 6))
            self.assertEqual(set(saved["kinds"]), g.known)
            self.assertTrue(any("First glance" in n for n in notes), notes)
            self.assertIn("First glance", screen.end_screen(g, before, 80, 24, notes))


if __name__ == "__main__":
    unittest.main()
