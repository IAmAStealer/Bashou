"""Logic fights: conditions in a shell script. `if`, `!` and `&&`/`||` read like English, and a single
flipped word lets the wrong people in. You fix the script, then `verify` runs it on every case."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from . import Challenge
from .repos import EDITORS

GUESTS = ["alice", "bruno", "chloe", "dimitri", "emma", "farid", "giulia", "hugo", "ines", "jonas"]
STRANGERS = ["mallory", "trudy", "eve", "oscar"]
FILES = ["notes.txt", "todo.txt", "journal.txt"]
FOLDERS = ["backup", "safe", "archive"]


def run(script, work, *args):
    """What the script prints, run with bash in `work` (empty when it hangs or bash is missing)."""
    try:
        done = subprocess.run(["bash", script.name, *args], cwd=work, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout.strip()


# --- Negation Gnome: a `!` that turns the guard around ----------------------------------------------

DOOR = """#!/bin/bash
# The party door: only the guests written in guests.txt may come in.
# Usage: bash door.sh NAME
if ! grep -qx "$1" guests.txt; then
  echo open
else
  echo closed
fi
"""


def door_setup(work, rng):
    guests = rng.sample(GUESTS, 4)
    (work / "guests.txt").write_text("\n".join(guests) + "\n")
    (work / "door.sh").write_text(DOOR)
    return {"guests": guests, "args": {"guest": guests[0], "stranger": rng.choice(STRANGERS)}}


def door_verify(work, meta, value):
    """Every guest gets open, every stranger closed, with the guest list read for real (a new name
    added to the list must get in too)."""
    script = work / "door.sh"
    if not script.is_file():
        return False
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copy(script, tmp / "door.sh")
        guests = meta["guests"] + ["zoe"]
        (tmp / "guests.txt").write_text("\n".join(guests) + "\n")
        return (all(run(tmp / "door.sh", tmp, g) == "open" for g in guests)
                and all(run(tmp / "door.sh", tmp, s) == "closed" for s in STRANGERS))


# --- Or Ogre: `||` where both conditions must hold ------------------------------------------------

SAVE = """#!/bin/bash
# Saves {file} into the folder {folder}/, but only when BOTH are there: the file and the folder.
if [ -f {file} ] || [ -d {folder} ]; then
  cp {file} {folder}/ && echo saved
else
  echo missing
fi
"""


def save_setup(work, rng):
    file, folder = rng.choice(FILES), rng.choice(FOLDERS)
    (work / "save.sh").write_text(SAVE.format(file=file, folder=folder))
    (work / file).write_text("buy bread\n")
    (work / folder).mkdir()
    return {"args": {"file": file, "folder": folder}}


def save_verify(work, meta, value):
    """The four cases, each in a fresh folder: saved only when the file and the folder are both there."""
    script = work / "save.sh"
    if not script.is_file():
        return False
    file, folder = meta["args"]["file"], meta["args"]["folder"]
    for has_file in (True, False):
        for has_folder in (True, False):
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                shutil.copy(script, tmp / "save.sh")
                if has_file:
                    (tmp / file).write_text("buy bread\n")
                if has_folder:
                    (tmp / folder).mkdir()
                want = "saved" if has_file and has_folder else "missing"
                if run(tmp / "save.sh", tmp) != want:
                    return False
                if want == "saved" and not (tmp / folder / file).is_file():
                    return False
    return True


LOGIC = dict(pet="owl", tools=EDITORS, requires=["bash", "grep"], skill="logic", fix=True)

ALL = [
    Challenge(level=1, id="negation_gnome", threat="Negation Gnome", **LOGIC,
              task="The Negation Gnome added one character to the party door, door.sh: now {guest} is left "
                   "outside and {stranger} walks in.\nFix door.sh so the guests of guests.txt get open and "
                   "everyone else gets closed. Try it with: bash door.sh {guest}. Then: verify",
              hints=["Read the if line aloud. grep -q finds the name quietly: it succeeds when the name is on "
                     "the list. The ! in front turns that answer around, so the if now means \"if the name is "
                     "NOT on the list, open\". Then run bash door.sh {guest} and bash door.sh {stranger} to "
                     "see the difference.",
                     "Remove the ! (and its space) from the if line: `if grep -qx \"$1\" guests.txt; then`. "
                     "With nano: nano door.sh, fix the line, Ctrl+O to save, Ctrl+X to quit. Or in one "
                     "command: sed -i 's/if ! grep/if grep/' door.sh"],
              setup=door_setup, verify=door_verify),
    Challenge(level=1, id="or_ogre", threat="Or Ogre", after=("negation_gnome",), **LOGIC,
              task="The Or Ogre swapped one word in save.sh: it should save {file} into {folder}/ only when both "
                   "are there, but now it also tries when one of them is missing, and cp fails.\nFix the "
                   "condition. Then: verify",
              hints=["|| means OR: the whole condition is true as soon as ONE side is true. && means AND: both "
                     "sides must be true. Here the script needs the file AND the folder. Try it: move the "
                     "folder away (mv {folder} gone), run bash save.sh, then put it back (mv gone {folder}).",
                     "On the if line, replace || with &&: `if [ -f {file} ] && [ -d {folder} ]; then`. With "
                     "nano: nano save.sh. Or in one command: sed -i 's/||/\\&\\&/' save.sh"],
              setup=save_setup, verify=save_verify),
]

# The Sage Owl's chest for the Logic path: the same flipped door, no enemy.
from .trials import trial  # noqa: E402

DOOR_CHEST = trial("trial_logic_door", 1, "A door script hides in this chest: door.sh. It lets strangers in and "
                   "keeps the guests of guests.txt out. Fix its condition. Then: verify",
                   ALL[0].hints, door_setup, door_verify, requires=["bash", "grep"], teaches=["if"])
CHESTS = [DOOR_CHEST]                    # locked chests in `bashou adventure`
