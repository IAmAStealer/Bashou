import base64
import ipaddress
import random
import re
import unittest
import uuid

from bashou import spot


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
        checks = {
            "ipv4": lambda t: ipaddress.IPv4Address(t),
            "ipv6": lambda t: ipaddress.IPv6Address(t),
            "mac": lambda t: self.assertRegex(t, r"^([0-9a-f]{2}[:-]){5}[0-9a-f]{2}$"),
            "uuid": lambda t: self.assertEqual(uuid.UUID(t).version, 4),
            "base64": lambda t: base64.b64decode(t, validate=True).decode(),
            "hex": lambda t: self.assertRegex(t, r"^(0x[0-9a-f]+|[0-9a-f]{2}( [0-9a-f]{2})*)$"),
            "md5": lambda t: self.assertRegex(t, r"^[0-9a-f]{32}$"),
            "sha1": lambda t: self.assertRegex(t, r"^[0-9a-f]{40}$"),
            "encrypted": lambda t: self.assertTrue(base64.b64decode(t).startswith(b"Salted__")),
            "jwt": lambda t: self.assertRegex(t, r"^eyJ[\w-]+\.eyJ[\w-]+\.[\w-]+$"),
            "basic": lambda t: self.assertRegex(base64.b64decode(t.split(" ")[1]).decode(), r"^\w+:\w+$"),
            "email": lambda t: self.assertRegex(t, r"^[\w.]+@\w+\.\w+$"),
            "url": lambda t: self.assertRegex(t, r"^https?://"),
            "regex": re.compile,
            "date": lambda t: self.assertRegex(t, r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$"),
            "timestamp": lambda t: self.assertRegex(t, r"^1[4-9]\d{8}$"),
        }
        for kind, (label, family, make) in spot.KINDS.items():
            for _ in range(50):
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

    def test_twenty_seconds_for_the_whole_game(self):
        g = self.game()
        self.clock.now = 19.9
        self.assertFalse(g.over())
        g.answer(self.right(g))
        self.clock.now = 20.0
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
            self.assertEqual(spot.play(Keys("\x1b[A", "r"), 80, 14), "restart")
            self.assertIsNone(spot.play(Keys("q"), 80, 14))

    def test_tiers(self):
        self.assertEqual(spot.tier(9), "")
        self.assertEqual(spot.tier(10), "Sharp eyes")
        self.assertEqual(spot.tier(30), "Eagle eyes")

    def test_the_string_in_the_middle_the_answers_around_the_clock_on_top(self):
        """Owner: the string right in the middle, little distraction, the time at the top of the terminal,
        the answers around the string with room around them."""
        for cols, rows in ((80, 14), (160, 48), (100, 30)):
            g = self.game()
            for _ in range(80):
                parts = spot.layout(g, cols, rows)
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
                rows_used = sorted({r for r, c, t, st in parts if t})
                self.assertEqual(rows_used[0], 1)                                            # the clock on top
                self.assertTrue(all(abs(r - mid) >= 3 for r in rows_used if r not in (1, rows, mid)))
                g.answer(random.choice(spot.ARROWS))
                if g.over():
                    g = self.game()

    def test_the_end_screen_fits(self):
        g = self.game()
        for line in spot.end_screen(g, 5, 80, 14).split("\n"):
            self.assertLessEqual(spot.visible_len(line.replace("\x1b[H\x1b[2J", "")), 80)

if __name__ == "__main__":
    unittest.main()
