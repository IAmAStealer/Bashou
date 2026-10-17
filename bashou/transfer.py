"""`bashou export` / `bashou import`: one save on two computers (owner, 2026-10-16).

The save travels as a small text file the player carries (a mail, its attachment, a chat): no server,
no account, nothing listens. Two modes:

- minimal (default): the meta progress only (achievements, pets no achievement brings back, lessons,
  fights beaten, adventure levels and chapters). Counters are rebuilt from the achievements
  (`Achievement.floor`), so no command, tool count or date leaves the computer.
- full: the whole save, minus what belongs to this computer (`LOCAL`).

Every value keeps the highest of this computer and the import. The block is checked by an HMAC with a
salt kept here. Bashou is open source, so the salt only stops hand edits and plain sha256 forgeries: a
player who reads this file can still cheat, on their own pet. Only a save of the same SAVE_VERSION
comes in: no migration on import, the other computer updates and exports again.
"""

import base64
import binascii
import copy
import datetime
import hashlib
import hmac
import json
import os
import re
import sys
import zlib
from pathlib import Path

from . import achievements, creatures, lesson, progress, state
from .adventure import world
from .i18n import _
from .render import BOLD, DIM, RESET

BEGIN, END = "-----BEGIN BASHOU SAVE-----", "-----END BASHOU SAVE-----"
SALT = b"bashou-save/v1:tBq7#pony-hooves-counted-from-1"
MODES = ("minimal", "full")
MAX_TEXT = 64 * 1024                # a pasted mail with a save in it is a few kilobytes
MAX_JSON = 256 * 1024               # what the block may unpack to (a zip bomb stops here)
LOCAL = {"version", "today", "threat", "threat_day", "last_threat", "update_checked", "update_available",
         "arena_closed_until", "badger_day", "evolving", "settings", "language", "active", "looks",
         "share_name", "win_times", "skills"}
# Counts no floor can rebuild: they read fights beaten (exported), projects or spot kinds. Owned, they stay.
NO_FLOOR = {"hunter", "bestiary", "wired", "network_engineer", "craftsman", "guild_master", "quick_study"}
ROAD = ("chapter", "leg", "segment", "distance", "leg_start", "topic", "hearts", "phase", "flawless")


class Refused(ValueError):
    """A block that doesn't come in. `why`: format, size, check, older, newer or field."""

    def __init__(self, why, message):
        super().__init__(message)
        self.why = why


# --- what travels ---------------------------------------------------------------------------------

def brought_back(s, pet):
    """Does an achievement of the save bring this pet back by itself (its unlock rule)?"""
    probe = {**state.default(), "achievements": list(s["achievements"])}
    return progress.unlock_rule(probe, pet)[0]


def passed(s):
    return [le["id"] for le in lesson.load() if lesson.mastered(s, le)]


def payload(s, mode="minimal"):
    if mode == "full":
        data = {k: copy.deepcopy(s[k]) for k in state.FIELDS if k not in LOCAL}
        data["lessons"] = {**data["lessons"], "passed": passed(s)}
        return data
    adv = s.get("adventure") or {}
    return {"achievements": list(s["achievements"]), "starter": s["starter"],
            "pets": [p for p in s["pets"] if not brought_back(s, p)], "ponies": list(s["ponies"]),
            "ladder_best": dict(s["ladder_best"]), "starter_best": s["starter_best"],   # forms kept from older rules
            "challenges": list(s["challenges"]),
            "lessons": {"read": list(lesson.read(s)), "met": list((s.get("lessons") or {}).get("met", [])),
                        "passed": passed(s), "right": list(lesson.right(s))},
            "adventure": {"levels": dict(adv.get("levels", {})), "chapters_done": adv.get("chapters_done", 0)}}


def sign(version, mode, raw):
    return hmac.new(SALT, f"{version}\n{mode}\n".encode() + raw, hashlib.sha256).hexdigest()


def encode(s, mode="minimal"):
    raw = json.dumps(payload(s, mode), separators=(",", ":"), sort_keys=True).encode()
    body = base64.b64encode(zlib.compress(raw, 9)).decode()
    version = str(state.SAVE_VERSION)
    return "\n".join([BEGIN, f"Version: {version}", f"Mode: {mode}",
                      *(body[i:i + 64] for i in range(0, len(body), 64)),
                      END, f"Check: {sign(version, mode, raw)}"]) + "\n"


# --- reading a block ------------------------------------------------------------------------------

def strings(value):
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def fits_minimal(data):
    shapes = {"achievements": strings, "pets": strings, "ponies": strings, "challenges": strings,
              "starter": lambda v: v is None or isinstance(v, str),
              "starter_best": lambda v: v is None or isinstance(v, str),
              "ladder_best": lambda v: isinstance(v, dict) and all(isinstance(x, str) for x in v.values()),
              "lessons": lambda v: isinstance(v, dict) and set(v) <= {"read", "met", "passed", "right"}
              and all(map(strings, v.values())),
              "adventure": lambda v: isinstance(v, dict) and set(v) <= {"levels", "chapters_done"}
              and isinstance(v.get("levels", {}), dict) and all(map(number, v.get("levels", {}).values()))
              and number(v.get("chapters_done", 0))}
    return set(data) <= set(shapes) and all(shapes[k](v) for k, v in data.items())


def fits_full(data):
    if not set(data) <= set(state.FIELDS) - LOCAL:
        return False
    lessons = data.get("lessons", {})
    if not isinstance(lessons, dict) or not strings(lessons.get("passed", [])):
        return False
    for name, value in data.items():
        try:
            if state.FIELDS[name][1](copy.deepcopy(value)) != value:
                return False
        except (ValueError, TypeError, KeyError, AttributeError):
            return False
    return True


def decode(text):
    """(mode, data) of a block found anywhere in `text` (a mail: quoted, rewrapped, CRLF), or Refused."""
    if len(text) > MAX_TEXT:
        raise Refused("size", _("This text is too long to be a Bashou save: copy only the lines from BEGIN to Check."))
    broken = Refused("format", _("No complete Bashou save in this text. Copy every line, from "
                                 "“-----BEGIN BASHOU SAVE-----” down to the “Check:” line."))
    lines = [re.sub(r"^[>\s]+", "", line).strip() for line in text.splitlines()]
    if BEGIN not in lines or END not in lines[lines.index(BEGIN):]:
        raise broken
    start = lines.index(BEGIN)
    end = lines.index(END, start)
    head = dict(line.split(":", 1) for line in lines[start + 1:end] if ":" in line)
    check = next((line.split(":", 1)[1].strip() for line in lines[end + 1:] if line.startswith("Check:")), "")
    version, mode = head.get("Version", "").strip(), head.get("Mode", "").strip()
    body = "".join(line for line in lines[start + 1:end] if ":" not in line).replace(" ", "")
    if not check or mode not in MODES or not version.isdigit():
        raise broken
    try:
        unpack = zlib.decompressobj()
        raw = unpack.decompress(base64.b64decode(body, validate=True), MAX_JSON)
    except (binascii.Error, ValueError, zlib.error):
        raise broken from None
    if unpack.unconsumed_tail:
        raise Refused("size", _("This save unpacks to far more than a real one: it was made by hand. Nothing changed."))
    if not unpack.eof:
        raise broken
    if not hmac.compare_digest(sign(version, mode, raw), check):
        raise Refused("check", _("This save was changed after Bashou wrote it (its Check line doesn't match), "
                                 "so it can't come in. Export it again on the other computer."))
    if int(version) < state.SAVE_VERSION:
        raise Refused("older", _("This save comes from an older Bashou. Run `bashou update` on the computer "
                                 "that made it, then `bashou export` again there."))
    if int(version) > state.SAVE_VERSION:
        raise Refused("newer", _("This save comes from a newer Bashou. Run `bashou update` here first, then import it again."))
    try:
        data = json.loads(raw)
    except ValueError:
        raise broken from None
    if not isinstance(data, dict) or not (fits_full if mode == "full" else fits_minimal)(data):
        raise Refused("field", _("This save holds something Bashou doesn't expect, so it can't come in. "
                                 "Export it again with the same Bashou version on both computers."))
    return mode, data


# --- merging --------------------------------------------------------------------------------------

def union(mine, theirs):
    """Local order kept, new ones appended."""
    return list(mine) + [x for x in dict.fromkeys(theirs) if x not in mine]


def best_per_key(mine, theirs, pick=max):
    return {**mine, **{k: pick(v, mine[k]) if k in mine else v for k, v in theirs.items()}}


def raise_to(s, path, add):
    """Add `add` to the save number at `path` ("tools.grep", "adventure.walked")."""
    *parents, last = path.split(".")
    node = s
    for key in parents:
        if not isinstance(node.get(key), dict):
            node[key] = world.new() if key == "adventure" else {}
        node = node[key]
    node[last] = (node.get(last) or 0) + add


def rebuild(s):
    """Counters at least as high as the achievements owned say they were (`Achievement.floor`)."""
    for a in achievements.ALL:
        if a.floor and a.id in s["achievements"]:
            now, goal = a.progress(s)
            if now < goal:
                raise_to(s, a.floor, goal - now)
    s["fights_won"] = max(s["fights_won"], len(s["challenges"]))


def satisfy(s, ids):
    """Lessons passed on the other computer stay passed: their count conditions are raised here."""
    by_id = lesson.by_id()
    for lid in ids:
        le = by_id.get(lid)
        if not le or lesson.mastered(s, le):
            continue
        for cond in le.get("masters", []):
            sides = [c.strip() for c in cond.split("|")]
            if any(lesson.met(s, c) for c in sides):
                continue
            kind, *args = next((c for c in sides if c.split()[0] in ("commands", "tool", "fights")), "-").split()
            if kind == "commands":
                s["commands"] = max(s["commands"], int(args[0]))
            elif kind == "tool":
                s["tools"][args[0]] = max(s["tools"].get(args[0], 0), int(args[1]))
            elif kind == "fights":
                s["fights_won"] = max(s["fights_won"], int(args[0]))


def rank(s, who, sprite):
    return progress.form_of(s, who, sprite) or 0


def merge_road(adv, theirs, full):
    if full:
        if (theirs.get("chapter", 1), theirs.get("leg", 0), theirs.get("distance", 0)) > \
                (adv["chapter"], adv["leg"], adv["distance"]):
            adv.update({k: theirs[k] for k in ROAD if k in theirs})
        for key in ("seen", "trials", "lessons"):
            adv[key] = union(adv.get(key, []), theirs.get(key, []))
        adv["bosses"] = adv.get("bosses", []) + [b for b in theirs.get("bosses", []) if b not in adv.get("bosses", [])]
        for key in ("walked", "correct"):
            adv[key] = max(adv.get(key, 0), theirs.get(key, 0))
    elif theirs.get("chapters_done", 0) > adv["chapters_done"]:
        adv.update(chapter=theirs["chapters_done"] + 1, leg=0, segment=0, topic=None, hearts=world.HEARTS,
                   phase="intro", leg_start=adv["distance"], flawless=True)
    adv["chapters_done"] = max(adv["chapters_done"], theirs.get("chapters_done", 0))
    adv["levels"] = best_per_key(adv.get("levels", {}), theirs.get("levels", {}))


def merge(local, data, mode):
    """The local save with the import in it: a new save, `local` and `data` untouched."""
    s, data, full = copy.deepcopy(local), copy.deepcopy(data), mode == "full"
    if not s["starter"] and data.get("starter") in creatures.STARTERS:
        s["starter"] = data["starter"]
    s["achievements"] = union(s["achievements"], [a for a in data.get("achievements", []) if a in achievements.BY_ID])
    s["challenges"] = union(s["challenges"], data.get("challenges", []))
    s["ponies"] = union(s["ponies"], [p for p in data.get("ponies", []) if p in creatures.FAMILIES])
    s["pets"] = union(s["pets"], [p for p in data.get("pets", []) if p in creatures.FAMILIES])
    theirs = data.get("lessons", {})
    mine = lesson.progress_of(s)
    for key in ("read", "met", "right"):
        mine[key] = union(mine[key], theirs.get(key, []))
    mine["opened"] = union(mine["opened"], theirs.get("opened", []) + theirs.get("read", []))
    if data.get("adventure") or s["adventure"]:
        s["adventure"] = {**world.new(), **(s["adventure"] or {})}
        merge_road(s["adventure"], data.get("adventure") or {}, full)
    if full:
        for key in ("commands", "fights_won", "fights_lost"):
            s[key] = max(s[key], data.get(key, 0))
        for key in ("tools", "constructs"):
            s[key] = best_per_key(s[key], data.get(key, {}))
        for key in ("days", "security"):
            s[key] = union(s[key], data.get(key, []))
        s["reviews"] = {**data.get("reviews", {}), **s["reviews"]}
        s["projects"]["done"] = best_per_key(s["projects"]["done"], data["projects"]["done"]) if "projects" in data else s["projects"]["done"]
        if "projects" in data:
            s["projects"]["days"] = union(s["projects"]["days"], data["projects"]["days"])
        if "spot" in data:
            for key in ("best", "games", "clean"):
                s["spot"][key] = max(s["spot"][key], data["spot"][key])
            s["spot"]["kinds"] = union(s["spot"]["kinds"], data["spot"]["kinds"])
    for pet, sprite in data.get("ladder_best", {}).items():
        if pet in creatures.FAMILIES and rank(s, pet, sprite) > rank(s, pet, s["ladder_best"].get(pet)):
            s["ladder_best"][pet] = sprite
    if s["starter"] == data.get("starter") and rank(s, "starter", data.get("starter_best")) > \
            rank(s, "starter", s["starter_best"]):
        s["starter_best"] = data["starter_best"]
    for pony in s["ponies"]:
        if pony not in s["pets"]:
            s["pets"].append(pony)
    satisfy(s, theirs.get("passed", []))
    rebuild(s)
    progress.check(s)
    s["evolving"], s["looks"] = copy.deepcopy(local["evolving"]), copy.deepcopy(local["looks"])
    state.clean(s)
    return s


def starter_name(starter):
    forms = creatures.STARTERS.get(starter)
    return _(creatures.PETS[forms[0]].name) if forms else starter


def summary(local, merged, data):
    """What the import brings, in lines (none: nothing new)."""
    lines = []
    new = [a for a in merged["achievements"] if a not in local["achievements"]]
    if new:
        lines.append(_("{n} new achievements").format(n=len(new)))
    pets = [p for p in merged["pets"] if p not in local["pets"]]
    if pets:
        lines.append(_("{n} new pets: {names}").format(
            n=len(pets), names=", ".join(_(creatures.NAMES[p]) for p in pets)))
    lessons = [le for le in passed(merged) if le not in passed(local)]
    if lessons:
        lines.append(_("{n} lessons passed").format(n=len(lessons)))
    before = (local.get("adventure") or {}).get("chapters_done", 0)
    after = (merged.get("adventure") or {}).get("chapters_done", 0)
    if after > before:
        lines.append(_("adventure: chapter {n} is next").format(n=after + 1))
    if merged["commands"] > local["commands"]:
        lines.append(_("{n} commands counted (here: {m})").format(n=f"{merged['commands']:,}", m=f"{local['commands']:,}"))
    if len(merged["days"]) > len(local["days"]):
        lines.append(_("{n} active days (here: {m})").format(n=len(merged["days"]), m=len(local["days"])))
    shown = ("achievements", "pets", "commands", "days", "evolving", "looks")
    if not lines and any(merged.get(k) != local.get(k) for k in state.FIELDS if k not in shown):
        lines.append(_("higher counts and records (tools, fights, adventure…)"))
    if lines and local["starter"] and data.get("starter") and data["starter"] != local["starter"]:
        lines.append(_("your starter here stays {name} (the other computer has {other})").format(
            name=starter_name(local["starter"]), other=starter_name(data["starter"])))
    return lines


# --- commands -------------------------------------------------------------------------------------

def write(s, mode, folder, today):
    """The block in a new file of `folder`, readable by you only. Never overwrites a file."""
    base = f"bashou-save-{'full-' if mode == 'full' else ''}{today}"
    text = encode(s, mode)
    for n in range(1, 1000):
        path = Path(folder) / (base + (f"-{n}" if n > 1 else "") + ".txt")
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        with os.fdopen(fd, "w") as f:
            f.write(text)
        return path
    raise FileExistsError(base)


def export(full=False):
    mode = "full" if full else "minimal"
    try:
        path = write(state.load(), mode, Path.cwd(), datetime.date.today().isoformat())
    except OSError as e:
        print("  " + _("Bashou couldn't write the save here ({error}). Go to a folder you can write in, "
                       "like your home folder (cd ~), and run it again.").format(error=e.strerror or e), file=sys.stderr)
        return 1
    print(f"  {BOLD}" + _("Your progress is saved in {path}").format(path=path) + RESET)
    print("  " + _("To play on another computer, attach this file to a mail to yourself, or paste its text "
                   "in the mail body. There, run `bashou import` and paste it, or `bashou import {name}`.").format(name=path.name))
    if mode == "minimal":
        print(f"  {DIM}" + _("Only your achievements, pets, lessons and adventure levels are in it: the counts "
                             "come back from your achievements. `bashou export --full` takes everything.") + RESET)
    return 0


def ask_input(question):
    try:
        return input(question)
    except EOFError:
        return ""


def load(text, ask=ask_input, out=sys.stdout):
    """Import the block of `text` after showing what it brings and asking. 0: done or nothing new."""
    try:
        mode, data = decode(text)
    except Refused as e:
        print("  " + str(e), file=out)
        return 1
    local = state.load()
    lines = summary(local, merge(local, data, mode), data)
    if not lines:
        print("  " + _("Nothing new in this save: this computer already has all of it."), file=out)
        return 0
    print(f"  {BOLD}" + _("This save brings:") + RESET, file=out)
    for line in lines:
        print("  • " + line, file=out)
    if ask("  " + _("Add it to your progress here? Nothing is lost: each count keeps its highest value. [y/N] ")
           ).strip().lower() not in ("y", "yes", "o", "oui"):
        print("  " + _("Nothing changed."), file=out)
        return 1
    from .cli import backup
    backup()
    with state.locked() as s:
        merged = merge(s, data, mode)
        s.clear()
        s.update(merged)
    print("  " + _("Done: your progress from the other computer is here."), file=out)
    return 0


def main(file=None):
    if file:
        try:
            with open(file, errors="replace") as f:
                text = f.read(MAX_TEXT + 1)
        except OSError as e:
            print("  " + _("Bashou can't read {file}: {error}").format(file=file, error=e.strerror or e), file=sys.stderr)
            return 1
    else:
        if sys.stdin.isatty():
            print("  " + _("Paste the save (every line from BEGIN to Check), then press Enter and Ctrl+D."))
        text = sys.stdin.read(MAX_TEXT + 1)
    return load(text)
