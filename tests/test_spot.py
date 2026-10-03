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


B64 = r"(?:[A-Za-z0-9+/]{4})+(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?"
OCTET = r"(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
# How a player who knows the kinds tells them apart, from the string alone: exactly one must match.
SPOTTER = {
    "ipv4": rf"^{OCTET}(\.{OCTET}){{3}}$",
    "ipv6": IPV6,
    "mac": MAC,
    "uuid": UUID4,
    "base64": rf"^(?!U2FsdGVkX1|0x)(?![0-9a-f]+$){B64}$",       # 0x…, all hex digits: hex or a hash
    "hex": r"^(0x[0-9a-f]+|[0-9a-f]{2}( [0-9a-f]{2})+)$",
    "md5": r"^[0-9a-f]{32}$",
    "sha1": r"^[0-9a-f]{40}$",
    "encrypted": r"^U2FsdGVkX1[A-Za-z0-9+/]*={0,2}$",               # openssl enc: "Salted__" in base64
    "jwt": r"^eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$",
    "basic": rf"^Basic {B64}$",
    "shadow": r"^\$1\$[./0-9A-Za-z]{1,8}\$[./0-9A-Za-z]{22}$",
    "csrf": r"^_csrf=[0-9A-Za-z]+-[A-Za-z0-9_-]{27}$",
    "oauth": r"^(\?code=[A-Za-z0-9_-]+&state=\w+|Bearer [A-Za-z0-9._~+/-]+=*)$",
    "email": r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
    "url": r"^https?://(www\.)?[a-z]+\.[a-z]{2,}(/[a-z]+){1,2}(\?[a-z]+=[a-z0-9]+)?$",
    "date": r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])(T([01]\d|2[0-3]):[0-5]\d:[0-5]\dZ)?$",
    "timestamp": r"^1\d{9}$",
    "regex": r"^[\^(]|\$$|\\[dwsb]|\][+{]|\w\?$|u\?",
    "python": r"^(def \w+\(.*\):|import \w+|for \w+ in \w+:|with open\(|if __name__|except \w+|print\(f\"|\w+ = \[.* for )",
    "rust": r"^(fn \w+\(|let (mut )?\w+|use std::|impl \w+|#\[derive|match \w+ \{)",
    "c": r"^(#include <|int main\(|char \*|printf\(\"|for \(int |struct \w+ \*|free\(|if \(\w+ == NULL\))",
    "bash": r"^(for \w+ in .*; do|if \[\[|grep |#!/usr/bin/env bash|\w+=\$\{|while read|echo |\[ \$#)",
    "sql": r"^(SELECT|INSERT INTO|UPDATE|CREATE TABLE|DELETE FROM|ALTER TABLE) ",
}


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class KindsTest(unittest.TestCase):
    """Owner: 20 kinds of strings seen in IT, generated at random (never the same twice)."""

    def test_twenty_kinds_each_generated_right(self):
        self.assertEqual(len(spot.KINDS), 24)
        rng = random.Random(1)
        def ipv6(t):
            self.assertRegex(t, IPV6)
            self.assertNotRegex(t, r"[A-F]|:::|(^|:)0[0-9a-f]")                  # lowercase, no leading zero
            self.assertTrue(all(len(g) <= 4 for g in t.split(":")) and t.count("::") <= 1)
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
            "shadow": lambda t: (self.assertRegex(t, r"^\$1\$[./0-9A-Za-z]{8}\$[./0-9A-Za-z]{22}$"),),
            "csrf": lambda t: self.assertRegex(t, r"^_csrf=[0-9A-Za-z]{6}-[A-Za-z0-9_-]{27}$"),
            "oauth": lambda t: self.assertRegex(t, r"^(\?code=[A-Za-z0-9_-]{22}&state=[a-z0-9]{3,5}|Bearer [A-Za-z0-9_-]{22})$"),
            "sha1": lambda t: self.assertRegex(t, r"^[0-9a-f]{40}$"),
            "encrypted": lambda t: (self.assertRegex(t, BASE64), self.assertTrue(t.startswith("U2FsdGVkX1"))),
            "jwt": jwt,
            "basic": lambda t: (self.assertRegex(t, r"^Basic " + BASE64[1:]),
                                self.assertRegex(base64.b64decode(t[6:]).decode(), r"^[^:]+:.+$")),
            "email": lambda t: self.assertRegex(t, r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"),
            "url": lambda t: (self.assertRegex(t, r"^https?://(www\.)?[a-z]+\.[a-z]{2,}(/[a-z]+){1,2}(\?[a-z]+=[a-z0-9]+)?$"),
                              self.assertTrue(urllib.parse.urlparse(t).netloc)),
            "regex": re.compile,
            "date": lambda t: (self.assertRegex(t, r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])"
                                                   r"(T([01]\d|2[0-3]):[0-5]\d:[0-5]\dZ)?$"),
                               datetime.datetime.fromisoformat(t.replace("Z", "+00:00"))),
            "timestamp": lambda t: (self.assertRegex(t, r"^[1-9]\d{9}$"),                 # 10 digits: 2001 to 2286
                                    self.assertTrue(2014 <= datetime.datetime.fromtimestamp(int(t)).year <= 2031)),
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


class SpotterTest(unittest.TestCase):
    """Owner: a base64 answered wrong. A player who only sees the string tells its kind by the rules above
    (strict regexes), never by what the game knows: every string must fit exactly one kind, the right one."""

    def spot(self, text):
        return [kind for kind, rule in SPOTTER.items() if re.search(rule, text)]

    def test_every_string_fits_one_kind_only(self):
        self.assertEqual(set(SPOTTER), set(spot.KINDS))
        rng = random.Random(7)
        for kind, (label, family, make) in spot.KINDS.items():
            for _ in range(2000):
                text = make(rng)
                self.assertEqual(self.spot(text), [kind], text)

    def test_a_player_reading_the_strings_wins_every_game(self):
        for seed in range(200):
            g = spot.Game(random.Random(seed), clock=Clock())
            while not g.over():
                found = self.spot(g.text)
                self.assertEqual(len(found), 1, g.text)
                labels = [spot.KINDS[k][0] for k in g.answers]          # what the screen shows
                g.answer(spot.ARROWS[labels.index(spot.KINDS[found[0]][0])])
            self.assertEqual((g.score, g.mistakes), (2 * len(spot.KINDS), 0), seed)


class RealFormatsTest(unittest.TestCase):
    """Owner (0.8.2): Linux password hashes, CSRF and OAuth2 strings, each reproducible at least one real way."""

    def test_md5crypt_is_openssl_s(self):
        self.assertEqual(spot.md5crypt("password", "abcdefgh"), "$1$abcdefgh$G//4keteveJp0qb8z2DxG/")   # openssl passwd -1
        import shutil, subprocess
        if shutil.which("openssl"):
            rng = random.Random(5)
            for _ in range(20):
                pw, salt = f"w{rng.randint(1, 10**6)}", "".join(rng.choice(spot.CRYPT64) for _ in range(rng.randint(1, 8)))
                done = subprocess.run(["openssl", "passwd", "-1", "-salt", salt, pw], capture_output=True, text=True)
                self.assertEqual(spot.md5crypt(pw, salt), done.stdout.strip(), (pw, salt))

    def test_csrf_token_is_the_csrf_library_s(self):
        import hashlib
        token = spot.csrf_token("Ab12Cd", "s3cret")
        digest = base64.b64encode(hashlib.sha1(b"Ab12Cd-s3cret").digest()).decode()
        self.assertEqual(token, "Ab12Cd-" + digest.replace("+", "-").replace("/", "_").replace("=", ""))   # pillarjs/csrf
