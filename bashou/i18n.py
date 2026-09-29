"""Translations. English is the source language; other languages live in locales/<lang>.json.

A catalog maps each English message to its translation. Missing or empty entries fall back to
English, so a language can ship half-translated.

    _("Commands")                        # code
    python3 -m bashou.translations       # add new messages to every catalog (empty values)

A new language is just a new file: locales/<code>.json with {"@language": "Deutsch"}, then run
the command above to fill it with every message to translate.
"""

import json
import os
import sys
from pathlib import Path

LOCALES = Path(__file__).resolve().parent / "locales"
NAME = "@language"                    # a catalog's own entry: the language's name, in that language


def _languages():
    found = {"en": "English"}
    for path in sorted(LOCALES.glob("*.json")):
        try:
            found[path.stem] = json.loads(path.read_text()).get(NAME) or path.stem
        except json.JSONDecodeError:
            pass
    return found


LANGUAGES = _languages()

_cache = {}
_lang = None


def saved():
    """The language chosen in the save. state.py plugs itself in here when it loads: i18n stays at the
    bottom of the imports, below the save that needs translated messages."""
    return None


def language():
    """BASHOU_LANG overrides the saved choice (handy for tests). Read once per process."""
    global _lang
    if _lang is None:
        _lang = os.environ.get("BASHOU_LANG") or saved() or "en"
    return _lang


def use(lang):
    """Switch language for this process (None: read the saved choice again)."""
    global _lang
    _lang = lang


def catalog(lang):
    if lang not in _cache:
        try:
            _cache[lang] = json.loads((LOCALES / f"{lang}.json").read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            _cache[lang] = {}
    return _cache[lang]


def _(text):
    lang = language()
    if lang == "en":
        return text
    return catalog(lang).get(text) or text


def cap(text):
    """Capitalize the first letter: a translation may start with a name like "une hydre des logs"."""
    return text[:1].upper() + text[1:]


def progress_of(lang):
    """(translated, total) messages for a language. `python3 -m bashou.translations` keeps every catalog
    holding exactly the messages of the code (tests/test_i18n.py checks it), so its own keys count."""
    keys = [k for k in catalog(lang) if k != NAME]
    return sum(bool(catalog(lang)[k]) for k in keys), len(keys)
