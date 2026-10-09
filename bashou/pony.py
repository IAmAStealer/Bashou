"""The hidden ponies (owner, 2026-10-09): a herd of secret pets, each hiding somewhere real.

`bashou pony` alone brings the Foal (only `bashou --help` mentions it). The others need a short word
found in a hiding place: the changelog, doc/easter_egg in the repository, the apt/dnf description, the
site's source, or a famous terminal joke the pet sees you type (cowsay, apt moo, make love...).
The words are only stored as hashes (and rot13 for the jokes' hints), so reading the code spoils nothing.
"""

import codecs
import hashlib
import re

from . import creatures, progress, render, state
from .i18n import _
from .render import BOLD, DIM, RESET

FOAL = "pony_foal"


def digest(word):
    return hashlib.sha256(word.strip().lower().encode()).hexdigest()[:16]


PONIES = {                       # digest of the word -> the pony it brings
    "9212e9c844fc6553": "pony_wrecking",      # CHANGELOG.md: the "Breaking change" line of every release
    "897abbb178d59a98": "pony_explorer",      # doc/easter_egg
    "4e30ea25cda1c18c": "pony_package",       # tools/package.py: the packages' short description
    "0470cc4e7d943c45": "pony_web",           # doc/install.html and doc/install.fr.html: an HTML comment
    "fc91368f2036677b": "pony_jealous",       # the rest: the jokes below
    "e46d6316c0eeda22": "pony_moo",
    "628fecb264d2e972": "pony_heart",
    "121b69a8d20269cf": "pony_library",
    "77e936e2e5b25a66": "pony_chef",
    "177b7cb0686749af": "pony_vim",
}

# Terminal jokes the pet notices: (pony, the command, its word in rot13). Typos and failures count
# too: `make love` and `:wq` always fail, that's the joke.
JOKES = [
    ("pony_jealous", re.compile(r"(^|[\s|;&(])cowsay\b"), "rail"),
    ("pony_moo", re.compile(r"(^|[\s;&(])apt(-get)?\s+moo\b"), "phq"),
    ("pony_heart", re.compile(r"(^|[\s;&(])make\s+love\s*$"), "uht"),
    ("pony_library", re.compile(r"(^|[\s;&(])man\s+woman\s*$"), "fuu"),
    ("pony_chef", re.compile(r"(^|[\s;&(])sudo\s+make\s+me\s+a\s+sandwich\s*$"), "pehzo"),
    ("pony_vim", re.compile(r"^\s*:(wq?|x|q)!?\s*$"), "rfp"),
]


def peeks():
    """What the pet says when a joke brings a pony: {pony: line}, `{word}` left to fill."""
    return {
        "pony_jealous": _("A pony peeks in, a little jealous of the cow. To welcome it: `bashou pony {word}`"),
        "pony_moo": _("Moo? A pony answers the cow. To welcome it: `bashou pony {word}`"),
        "pony_heart": _("No rule to make love… but a pony comes for a hug. To welcome it: `bashou pony {word}`"),
        "pony_library": _("No manual for that, but a pony brings you a book. To welcome it: `bashou pony {word}`"),
        "pony_chef": _("Okay, a sandwich. A pony in a chef's hat brings it. To welcome it: `bashou pony {word}`"),
        "pony_vim": _("You're not in vim anymore! A pony who knows the feeling peeks in. To welcome it: "
                      "`bashou pony {word}`"),
    }


def where():
    """What each pony says when it arrives: where you found it, and what that teaches."""
    return {
        "pony_foal": _("You found me in `bashou --help`. Most programs answer to `--help` with a summary of "
                       "their options, so curious people try it first. Keep doing that with every new tool."),
        "pony_wrecking": _("You found me in the changelog. Every Bashou release lists what changed, and a "
                           "\"breaking change\" is one that stops an old habit from working. Reading the "
                           "changelog before updating saves you surprises."),
        "pony_explorer": _("You found me in doc/easter_egg, deep in Bashou's repository. Reading a project's "
                           "files is how you learn how it really works, and nothing in there can break."),
        "pony_package": _("You found me in the package description that `apt search` and `dnf search` show. "
                          "Those searches read the name and short description of every package they know."),
        "pony_web": _("You found me in an HTML comment in the source of Bashou's site. Browsers hide comments, "
                      "but View source (Ctrl+U) shows everything a page is made of."),
        "pony_jealous": _("You ran `cowsay`, the program that makes a cow say your text. I can talk too, you "
                          "know! Try `fortune | cowsay` to see a pipe at work."),
        "pony_moo": _("You ran `apt moo`, a joke hidden in apt for years. Developers love hiding jokes in "
                      "their tools: they reward people who try things."),
        "pony_heart": _("You ran `make love`. make builds the targets of a Makefile, and there is no target "
                        "called love, so it answers \"No rule to make target\": a joke as old as make."),
        "pony_library": _("You ran `man woman`. man opens the manual of a command, and there is no command "
                          "called woman: \"No manual entry for woman\" is a very old Unix joke."),
        "pony_chef": _("You ran `sudo make me a sandwich`, from xkcd comic 149. sudo runs a command as the "
                       "administrator, so this time nobody can say no."),
        "pony_vim": _("You typed `:wq` in the shell. That's how vim saves and quits, and you were already out "
                      "of vim! bash doesn't know `:wq`, so it said \"command not found\"."),
    }


def herd():
    """The ponies, in board order."""
    return [pet for pet in creatures.NAMES if creatures.FAMILIES[pet].herd == "pony"]


def peek(s, line):
    """A terminal joke that brings a pony you don't have yet: the pet's line, or None."""
    for pony, pattern, word in JOKES:
        if pony not in s["ponies"] and pattern.search(line):
            return "🐴 " + peeks()[pony].format(word=codecs.decode(word, "rot13"))
    return None


def show(pony):
    """The pony, then where it was found."""
    pet = creatures.get(creatures.FAMILIES[pony].first)
    cells = [[True] * pet.width for _ in range(len(pet.base) // 2)]
    print()
    for line in render.lines(pet, [], cells):
        print("  " + line.replace(render.SKIP, " "))
    cols = render.columns()
    print(f"\n  {BOLD}{_(creatures.NAMES[pony])}{RESET} {DIM}{_(creatures.FAMILIES[pony].voice)}{RESET}")
    for line in render.wrap(where()[pony], max(30, min(cols, 80) - 3), 8):
        print("  " + line)


def main(word=None):
    pony = FOAL if not word else PONIES.get(digest(word))
    if not pony:
        print("  " + _("No pony answers to that name."))
        return 1
    with state.locked() as s:
        new = pony not in s["ponies"]
        if new:
            s["ponies"].append(pony)
            notes = progress.check(s)
        mine = sum(p in s["ponies"] for p in herd())
    show(pony)
    print()
    if new:
        for note in notes:
            print("  " + note)
    else:
        print("  " + _("{name} is already in your herd.").format(name=_(creatures.NAMES[pony])))
    print(f"  {DIM}" + _("Ponies found: {n}/{total}.").format(n=mine, total=len(herd())) + RESET)
    return 0
