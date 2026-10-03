"""The share page (doc/site): anyone can write the link it reads, so it must stay locked down."""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from bashou import creatures, render, share, state

SITE = Path(__file__).resolve().parent.parent / "doc/site"


class SharePageTest(unittest.TestCase):
    def setUp(self):
        self.html = (SITE / "share.html").read_text()
        self.js = (SITE / "share.js").read_text()

    def test_locked_page(self):
        csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', self.html).group(1)
        for rule in ("default-src 'none'", "script-src 'self'", "base-uri 'none'", "form-action 'none'"):
            self.assertIn(rule, csp)
        self.assertNotIn("unsafe", csp)
        self.assertIn('name="referrer" content="no-referrer"', self.html)
        self.assertNotRegex(self.html, r"<script>|<script [^>]*>[^<]")             # no inline code
        self.assertNotRegex(self.html, r"\son\w+=")                                  # no onclick=…
        self.assertNotRegex(self.html, r"https?://(?!github\.com/IAmAStealer/Bashou)")  # nothing loaded from elsewhere

    def test_no_dangerous_calls(self):
        for bad in ("innerHTML", "outerHTML", "insertAdjacentHTML", "eval(", "new Function", "document.write",
                    "setTimeout(\"", "localStorage", "cookie"):
            self.assertNotIn(bad, self.js)
        self.assertEqual(re.findall(r'fetch\("([^"]+)"', self.js), ["share-pets.json"])

    def test_same_keys_and_name_rule_as_bashou(self):
        keys = re.search(r"const KEYS = \[([^\]]+)\]", self.js).group(1)
        self.assertEqual(re.findall(r'"(\w+)"', keys), list(share.KEYS))
        self.assertIn(share.NAME.pattern.join("^$"), self.js.replace("\\/", "/"))

    def test_page_data_draws_every_family(self):
        data = share.page_data()
        for family, info in data["families"].items():
            self.assertEqual(len(info["forms"]), len(info["en"]))
            self.assertEqual(len(info["forms"]), len(info["fr"]))
            for sprite in info["forms"]:
                self.assertIn(sprite, data["sprites"])
        s = state.default()
        s["starter"] = "sprout"
        card = share.payload(s)
        self.assertIn(card["p"], data["families"])

    @unittest.skipUnless(shutil.which("node"), "node isn't installed")
    def test_hostile_links_are_refused(self):
        s = state.default()
        s["starter"] = "star"
        good = share.link(share.payload(s, "Alexis"))
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["python3", str(SITE.parent.parent / "tools/package.py"), "site", tmp], check=True)
            done = subprocess.run(["node", str(Path(__file__).with_name("share_page.js")), f"{tmp}/share.js",
                                   f"{tmp}/share-pets.json", good], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


class SamePixelArtTest(unittest.TestCase):
    """The banner must show the pets exactly as Bashou draws them in the terminal (owner, 0.6.1)."""

    def expected(self, sprite_id):
        pet = creatures.load(Path(creatures.__file__).parent / "pets" / f"{sprite_id}.json")
        return {f"{r},{c}": pet.palette[k] if isinstance(pet.palette[k], str) else "#%02x%02x%02x" % pet.palette[k]
                for r, row in enumerate(render.grid(pet, [])) for c, k in enumerate(row) if k != "."}

    def test_the_page_data_is_bashou_s_pets(self):
        data = share.page_data()
        for family, info in data["families"].items():
            if family in creatures.STARTERS:
                self.assertEqual(info["forms"], list(creatures.STARTERS[family]))
            else:
                self.assertEqual(info["forms"], list(creatures.forms(family)))
                self.assertEqual(info["en"], creatures.names(family))
        for sprite_id, sprite in data["sprites"].items():
            cells = {f"{r},{c}": sprite["palette"][k] for r, row in enumerate(sprite["base"])
                     for c, k in enumerate(row) if k != "."}
            self.assertEqual({k: v.lower() for k, v in cells.items()},
                             {k: v.lower() for k, v in self.expected(sprite_id).items()}, sprite_id)

    @unittest.skipUnless(shutil.which("node"), "node isn't installed")
    def test_the_page_paints_the_same_pixels(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["python3", str(SITE.parent.parent / "tools/package.py"), "site", tmp], check=True)
            done = subprocess.run(["node", str(Path(__file__).with_name("share_pixels.js")), f"{tmp}/share.js",
                                   f"{tmp}/share-pets.json"], capture_output=True, text=True, check=True)
        painted = json.loads(done.stdout)
        self.assertEqual(set(painted), set(share.page_data()["sprites"]))
        for sprite_id, cells in painted.items():
            self.assertEqual({k: v.lower() for k, v in cells.items()},
                             {k: v.lower() for k, v in self.expected(sprite_id).items()}, sprite_id)


class HomePageTest(unittest.TestCase):
    """Owner (0.8.2): be found by people who search "learn linux commands", "bash scripting"… (Google Trends)."""

    def test_the_home_page_says_what_people_search(self):
        html = (SITE.parent / "install.html").read_text()
        title = re.search(r"<title>([^<]+)</title>", html).group(1)
        description = re.search(r'<meta name="description" content="([^"]+)"', html).group(1)
        for words in ("terminal pet", "Linux commands", "bash scripting"):          # the 3 most searched
            self.assertIn(words, title)
        self.assertLessEqual(len(description), 200)
        self.assertIn('rel="canonical" href="https://iamastealer.github.io/Bashou/"', html)
        for picture in re.findall(r'<img src="([^"]+)"', html):
            self.assertTrue((SITE.parent / picture).exists(), picture)

    def test_the_site_has_a_sitemap_and_cards_stay_out_of_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["python3", str(SITE.parent.parent / "tools/package.py"), "site", tmp], check=True)
            self.assertIn("<loc>https://iamastealer.github.io/Bashou/</loc>", (Path(tmp) / "sitemap.xml").read_text())
            for picture in ("prompt.svg", "duel.svg", "share.png"):
                self.assertTrue((Path(tmp) / "img" / picture).exists())
        self.assertIn('<meta name="robots" content="noindex">', (SITE / "share.html").read_text())
