import json
import re
import unittest

from bashou import i18n


class CatalogTest(unittest.TestCase):
    def tearDown(self):
        i18n.use(None)

    def test_every_message_is_in_every_catalog(self):
        """Run `python3 -m bashou.i18n` after adding or changing a message."""
        keys = set(i18n.messages())
        for lang in i18n.LANGUAGES:
            if lang != "en":
                self.assertEqual(set(i18n.catalog(lang)) - {i18n.NAME}, keys, f"{lang}: run python3 -m bashou.i18n")
                self.assertTrue(i18n.catalog(lang).get(i18n.NAME), f"{lang}: needs its \"@language\" name")

    def test_placeholders_survive_translation(self):
        for lang in i18n.LANGUAGES:
            if lang == "en":
                continue
            for key, value in i18n.catalog(lang).items():
                if value:
                    self.assertEqual(sorted(re.findall(r"{\w*}", key)), sorted(re.findall(r"{\w*}", value)),
                                     f"{lang}: {key!r}")

    def test_missing_translation_falls_back_to_english(self):
        i18n.use("fr")
        i18n._cache["fr"] = {"Commands": "Commandes", "Pets": ""}
        try:
            self.assertEqual(i18n._("Commands"), "Commandes")
            self.assertEqual(i18n._("Pets"), "Pets")
            self.assertEqual(i18n._("never seen"), "never seen")
        finally:
            i18n._cache.pop("fr")

    def test_adventure_names_are_translatable(self):
        """Boss names, chapter titles and places went through _() but weren't in the catalogs."""
        from bashou.adventure import world
        keys = set(i18n.messages())
        self.assertIn("Kernel Warden", keys)
        self.assertIn("The Sleepy Meadow", keys)
        ch = world.chapter(9)
        self.assertIn(ch["title"], keys)
        i18n.use("fr")
        i18n._cache["fr"] = {ch["title"]: "Lac des paquets perdus"}
        try:
            self.assertEqual(world.title(ch), "Lac des paquets perdus (9)")
        finally:
            i18n._cache.pop("fr")

    def test_catalogs_are_valid_json(self):
        for path in i18n.LOCALES.glob("*.json"):
            json.loads(path.read_text())


if __name__ == "__main__":
    unittest.main()
