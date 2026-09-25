import unittest

from bashou import qr, share, skills, state


def player(**extra):
    s = state.default()
    s.update(starter="pebble", commands=1234, fights_won=7, **extra)
    s["tools"] = {"grep": 40, "ssh": 3}
    s["days"] = ["2026-09-20", "2026-09-21"]
    return s


class ShareTest(unittest.TestCase):
    def test_only_whitelisted_numbers_and_ids(self):
        data = share.payload(player())
        self.assertLessEqual(set(data), set(share.KEYS))
        self.assertEqual(data["p"], "pebble")
        for key in ("f", "lv", "ach", "pets", "won", "read"):
            self.assertIsInstance(data[key], int)
        text = share.link(data)
        for private in ("grep", "ssh", "2026", "1234"):             # tools, dates, command count stay home
            self.assertNotIn(private, str(data))
            self.assertNotIn(private, text.split("#")[0])

    def test_link_round_trip(self):
        data = share.payload(player(skills=["bash", "network"]), "Alexis_42")
        self.assertEqual(share.decode(share.link(data)), data)
        self.assertTrue(share.link(data).startswith("https://iamastealer.github.io/Bashou/share.html#v1."))

    def test_the_longest_card_fits_a_small_qr_code(self):
        data = share.payload(player(skills=sorted(skills.SKILLS)), "x" * 12)
        data.update(lv=20, ach=999, pets=64, won=99999, read=999)
        url = share.link(data)
        self.assertLess(len(url), 300)
        self.assertLessEqual(len(qr.encode(url)), 17 + 4 * 10)

    def test_the_name_filter(self):
        for good in ("Alexis", "a", "x_y-Z9", "abcdefghijkl"):
            self.assertTrue(share.NAME.fullmatch(good), good)
        for bad in ("", "two words", "<b>", "é", "🐱", "abcdefghijklm", "a\nb", "a;rm"):
            self.assertFalse(share.NAME.fullmatch(bad), bad)
        self.assertNotIn("n", share.payload(player(), "<script>"))   # a bad saved name is dropped

    def test_every_payload_says_what_it_shares(self):
        rows = dict(share.describe(share.payload(player(), "Alexis")))
        self.assertEqual(rows["Name"], "Alexis")
        self.assertEqual(rows["Fights won"], "7")
