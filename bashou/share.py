"""`bashou share`: a QR code to show your progress on a phone, then share it as an image.

Nothing is sent anywhere. The QR code holds a link to a static page on Bashou's GitHub Pages; the
progress travels after the `#`, which browsers never send to the server. The page draws the banner on
the phone. Only what `payload` lists is shared: no commands, paths, names of machines or dates.
"""

import base64
import json
import re
import sys
import zlib

from pathlib import Path

from . import achievements, i18n, progress, qr, skills, state
from .creatures import NAMES, PETS, STARTERS, owned
from . import creatures
from .i18n import _
from .repo_setup import SITE
from .render import BOLD, DIM, RESET

PAGE = f"{SITE}/share.html"
NAME = re.compile(r"[A-Za-z0-9_-]{1,12}")      # the page accepts exactly the same (share.js)
KEYS = ("p", "f", "lv", "ach", "pets", "won", "read", "sk", "n", "s", "sf", "spot", "r")
# Rare pets, after the fully grown ones: the hardest to meet (two secrets, strace, kubectl, gpg and pass).
HARD = ("cat", "honey_badger", "spider", "whale", "leopard")
MAX_RARE = 10


def payload(s, name=""):
    """What the card shows: the active pet (family and form), the starter and its latest form, numbers,
    skills and the nickname."""
    who = progress.who_of(s)
    starter = s["starter"] or "star"
    family = starter if who == "starter" else who
    data = {"p": family, "f": progress.look(s, who), "lv": progress.starter_level(s),
            "ach": len(achievements.earned(s)), "pets": len(owned(s)), "won": s["fights_won"],
            "read": len((s.get("lessons") or {}).get("read", [])),
            "sk": [] if s["skills"] == "all" else sorted(s["skills"]),
            "s": starter, "sf": progress.reached(s, "starter"),
            "spot": s["spot"]["best"],
            "r": ",".join(f"{pet}{form}" for pet, form in rare(s))}
    if name and NAME.fullmatch(name):
        data["n"] = name
    return fit(data)


def fit(data):
    """The link must fit a QR code a terminal can show: drop the last rare pets, then the spot score."""
    while True:
        try:
            qr.encode(link(data))
            return data
        except ValueError:
            if data["r"]:
                data["r"] = data["r"].rpartition(",")[0]
            elif "spot" in data:
                del data["spot"], data["r"]
            else:
                raise


def rare_pets(data):
    """[(pet, form)] from the card's "r": "bat3,cat1"."""
    return [(m.group(1), int(m.group(2))) for m in re.finditer(r"([a-z_]+)(\d+)", data.get("r", ""))]


def rare(s):
    """[pet, form] of the rare pets: every pet grown to its last form (board order), then the hard ones."""
    pets = owned(s)
    grown = [p for p in pets if len(creatures.forms(p)) > 1 and progress.reached(s, p) == len(creatures.forms(p))]
    hard = [p for p in HARD if p in pets and p not in grown]
    return [[p, progress.reached(s, p)] for p in sorted(grown, key=list(NAMES).index) + hard][:MAX_RARE]


def encode(data):
    raw = json.dumps(data, separators=(",", ":")).encode()
    return "v1." + base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode().rstrip("=")


def decode(text):
    """The payload back from a link's fragment (tests, and what the page does in JavaScript)."""
    body = text.split("#", 1)[-1]
    if not body.startswith("v1."):
        raise ValueError("unknown version")
    body = body[3:]
    return json.loads(zlib.decompress(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))))


def link(data):
    return f"{PAGE}#{encode(data)}"


def describe(data):
    """The payload in plain words, shown before the QR code."""
    who = data["p"]
    if who in STARTERS:
        sprite, name = progress.sprite_of({"starter": who}, "starter", data["f"])
    else:
        sprite, name = progress.sprite_of({}, who, data["f"])
    starter = progress.sprite_of({"starter": data["s"]}, "starter", data["sf"])[1]
    rows = [(_("Pet"), name), (_("Starter"), starter), (_("Level"), str(data["lv"])), (_("Achievements"), str(data["ach"])),
            (_("Pets"), str(data["pets"])), (_("Fights won"), str(data["won"])),
            (_("Lessons read"), str(data["read"])),
            (_("Skills"), ", ".join(data["sk"]) or _("a bit of everything"))]
    if "spot" in data:
        rows.append((_("Best in bashou spot"), str(data["spot"])))
    if data.get("r"):
        rows.append((_("Rare pets"), ", ".join(progress.sprite_of({}, p, f)[1] for p, f in rare_pets(data))))
    if "n" in data:
        rows.insert(0, (_("Name"), data["n"]))
    return rows


# Upper bounds the page accepts (share.js reads them from share-pets.json).
BOUNDS = {"lv": (1, progress.MAX_LEVEL), "ach": (0, 999), "pets": (0, 99), "won": (0, 99999), "read": (0, 999),
          "spot": (0, 999), "r": (0, MAX_RARE)}          # r: how many rare pets


def page_data():
    """share-pets.json, published next to share.html: every family's forms and their sprites, the skills
    and the bounds. The page only draws what is listed here."""
    pets = Path(__file__).parent / "pets"
    fr = i18n.catalog("fr")
    families, sprites = {}, {}
    lines = [(line, list(chain), [PETS[f].name for f in chain]) for line, chain in STARTERS.items()]
    lines += [(pet, list(creatures.forms(pet)), creatures.names(pet)) for pet in NAMES]
    for family, forms, names in lines:
        families[family] = {"forms": forms, "en": names, "fr": [fr.get(n) or n for n in names]}
        for sprite in forms:
            d = json.loads((pets / f"{sprite}.json").read_text())
            sprites[sprite] = {"palette": d["palette"], "base": d["base"]}
    labels = {k: {"en": v.split(":")[0], "fr": (fr.get(v) or v).split(":")[0].strip()} for k, v in ((k, s.text) for k, s in skills.SKILLS.items())}
    return {"families": families, "sprites": sprites, "skills": labels, "starters": list(STARTERS), "bounds": BOUNDS}


def ask_name():
    """A nickname typed at the prompt, or None (Ctrl+C, Ctrl+D, or no terminal to ask in)."""
    if not sys.stdin.isatty():
        return None
    print("  " + _("Your card needs a nickname: it shows on the image instead of your real name."))
    while True:
        try:
            name = input("  " + _("Nickname (1 to 12 letters, digits, - or _): ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if NAME.fullmatch(name):
            return name
        print("  " + _("A name is 1 to 12 letters, digits, - or _ (no spaces): it shows on the image."))


def main(args):
    name = args.name if args.name is not None else state.load().get("share_name", "")
    if args.name is not None and not NAME.fullmatch(args.name):
        print("  " + _("A name is 1 to 12 letters, digits, - or _ (no spaces): it shows on the image."))
        return 1
    if not NAME.fullmatch(name or ""):
        name = ask_name()                              # asked outside the lock: other terminals keep going
        if not name:
            print("  " + _("A card needs a nickname: bashou share --name NICK"))
            return 1
    with state.locked() as s:
        s["share_name"] = name
        data = payload(s, name)
    print("\n  " + BOLD + _("This is all your card shares:") + RESET)
    rows = describe(data)
    width = max(len(label) for label, _v in rows)
    for label, value in rows:
        print(f"    {label:<{width}}  {value}")
    print(f"  {DIM}" + _("No commands, files, machine names or dates. Change the nickname with bashou share --name NICK.")
          + RESET + "\n")
    url = link(data)
    for line in qr.terminal(qr.encode(url)):
        print("  " + line)
    print("\n  " + _("Scan it with your phone: the page draws your banner, then Share sends it to Signal, "
                     "WhatsApp or any app."))
    print(f"  {DIM}" + _("Your progress stays in the link, after the #: browsers never send that part to the "
                         "server.") + RESET)
    print(f"  {DIM}{url}{RESET}\n")
    return 0
