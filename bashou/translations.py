"""Which messages there are to translate, and how much of each language is done.

    python3 -m bashou.translations       # add new messages (empty) to every catalog, show progress

It reads every module and data table, so it sits on top of everything (i18n itself only translates).
"""

import ast
import json
import sys
from pathlib import Path

from . import achievements, behavior, challenges, cli, creatures, dialogue, learn, progress, safety, skills, state
from .adventure import lessons, world
from .i18n import LANGUAGES, LOCALES, NAME, catalog


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
    found = []
    for path in sorted(Path(__file__).resolve().parent.rglob("*.py")):
        found += _calls(path)
    for a in achievements.ALL:
        found += [a.name, a.how]
    for table in (dialogue.TRAITS, dialogue.INVITES, dialogue.DISCOVER):
        for lines in table.values():
            found += lines
    found += dialogue.TYPO_FIX + dialogue.TYPO_NONE + dialogue.PROJECT_NUDGES
    from .project import LEVELS
    found += LEVELS
    for family in creatures.FAMILIES.values():
        found += [family.voice] + family.tips + family.personal + [t for t in (family.name, family.blurb,
                                                                              family.unlock.get("how")) if t]
    found += safety.messages()
    for chain in list(creatures.FORMS.values()) + list(creatures.STARTERS.values()):
        found += [creatures.PETS[s].name for s in chain]
    found += list(behavior.ACTIONS.values())
    found += [boss for name, home, boss in world.TOPICS.values()] + world.PLACES + [world.NEW_ROAD]
    for ch in world.CHAPTERS:
        found += [ch["title"], ch["intro"]]
    for lesson in lessons.LESSONS:
        found += [lesson["title"]] + [text for text, example in lesson["pages"]]
    found += list(progress.CONSTRUCT_NAMES.values())
    found += [setting.help for setting in state.SETTINGS.values()]
    found += [skill.text for skill in skills.SKILLS.values()]
    found += list(learn.COMMANDS.values()) + list(learn.SYNTAX.values())
    found += [m for flags in learn.FLAGS.values() for m in flags.values()]
    found += [m for subs in learn.SUBCOMMANDS.values() for m in subs.values()]
    found += [m for roles in learn.ARGS.values() for m in roles]
    for ch in challenges.ALL + challenges.SECURITY + challenges.TRIALS:
        found += [ch.threat, ch.task, *ch.hints] + ([ch.help] if ch.help else [])
    found.append(challenges.HELP_HINT)
    found += [cli.PET, cli.LEARN, cli.PLAY, cli.SETTINGS] + [c.row[1] for c in cli.COMMANDS if c.row]
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
