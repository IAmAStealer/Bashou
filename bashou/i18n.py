"""Translations. English is the source language; other languages live in locales/<lang>.json.

A catalog maps each English message to its translation. Missing or empty entries fall back to
English, so a language can ship half-translated.

    _("Commands")                        # code
    python3 -m bashou.i18n               # add new messages to every catalog (empty values)

A new language is just a new file: locales/<code>.json with {"@language": "Deutsch"}, then run
the command above to fill it with every message to translate.
"""

import ast
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


def language():
    """BASHOU_LANG overrides the saved choice (handy for tests). Read once per process."""
    global _lang
    if _lang is None:
        from . import state
        _lang = os.environ.get("BASHOU_LANG") or state.load().get("language") or "en"
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
    """(translated, total) messages for a language."""
    cat = catalog(lang)
    keys = messages()
    return sum(bool(cat.get(k)) for k in keys), len(keys)


# --- extraction ---------------------------------------------------------------

def _calls(path):
    """String literals passed to _() in a source file."""
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_"
                and node.args and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            yield node.args[0].value


def messages():
    """Every translatable message: _() calls in the code plus the data tables."""
    from . import achievements, behavior, challenges, creatures, dialogue
    found = []
    for path in sorted(Path(__file__).resolve().parent.rglob("*.py")):
        found += _calls(path)
    for a in achievements.ALL:
        found += [a.name, a.how]
    for table in (dialogue.TIPS, dialogue.PERSONAL, dialogue.TRAITS, dialogue.INVITES, dialogue.DISCOVER):
        for lines in table.values():
            found += lines
    found += dialogue.TYPO_FIX + dialogue.TYPO_NONE + list(dialogue.VOICE.values())
    from . import safety
    found += safety.messages()
    found += list(creatures.NAMES.values()) + list(creatures.FORM_NAMES.values())
    found += list(creatures.STARTER_BLURBS.values())
    for names in creatures.STAGES.values():
        found += names
    found += list(behavior.ACTIONS.values())
    from . import progress
    from .adventure import lessons
    from .adventure import world
    found += [boss for name, home, boss in world.TOPICS.values()] + world.PLACES + [world.NEW_ROAD]
    for ch in world.CHAPTERS:
        found += [ch["title"], ch["intro"]]
    for lesson in lessons.LESSONS:
        found += [lesson["title"]] + [text for text, example in lesson["pages"]]
    found += list(progress.CONSTRUCT_NAMES.values()) + [how for rule, how in progress.STATE_PETS.values()]
    from . import state
    found += [text for default, text in state.SETTINGS.values()]
    from . import skills
    found += list(skills.SKILLS.values())
    from . import learn
    found += list(learn.COMMANDS.values()) + list(learn.SYNTAX.values())
    found += [m for flags in learn.FLAGS.values() for m in flags.values()]
    found += [m for subs in learn.SUBCOMMANDS.values() for m in subs.values()]
    found += [m for roles in learn.ARGS.values() for m in roles]
    from . import explain
    found += [text for topics in explain.NOTES.values() for text, example in topics.values()]
    for ch in challenges.ALL + challenges.SECURITY + challenges.TRIALS:
        found += [ch.threat, ch.task, *ch.hints] + ([ch.help] if ch.help else [])
    found.append(challenges.HELP_HINT)
    return list(dict.fromkeys(found))


def update():
    """Add missing messages (empty) to every catalog and drop ones no longer used."""
    keys = messages()
    LOCALES.mkdir(exist_ok=True)
    for lang in LANGUAGES:
        if lang == "en":
            continue
        path = LOCALES / f"{lang}.json"
        old = json.loads(path.read_text()) if path.exists() else {}
        new = {NAME: old.get(NAME) or lang, **{k: old.get(k, "") for k in keys}}
        path.write_text(json.dumps(new, ensure_ascii=False, indent=1) + "\n")
        done = sum(bool(new[k]) for k in keys)
        print(f"{lang}: {done}/{len(keys)} translated")


if __name__ == "__main__":
    sys.exit(update())
