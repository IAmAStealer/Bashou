"""`bashou share`: a QR code to show your progress on a phone, then share it as an image.

Nothing is sent anywhere. The QR code holds a link to a static page on Bashou's GitHub Pages; the
progress travels after the `#`, which browsers never send to the server. The page draws the banner on
the phone. Only what `payload` lists is shared: no commands, paths, names of machines or dates.
"""

import base64
import json
import re
import zlib

from . import achievements, progress, qr, state
from .creatures import FORM_NAMES, FORMS, ROSTER, STAGES, STARTERS, owned
from .i18n import _
from .repo_setup import SITE

BOLD, DIM, RESET = "\x1b[1m", "\x1b[2m", "\x1b[0m"
PAGE = f"{SITE}/share.html"
NAME = re.compile(r"[A-Za-z0-9_-]{1,12}")      # the page accepts exactly the same (share.js)
KEYS = ("p", "f", "lv", "ach", "pets", "won", "read", "sk", "n")


def payload(s, name=""):
    """What the card shows: the active pet (family and form), numbers, skills and an optional nickname."""
    who = progress.who_of(s)
    family = (s["starter"] or "star") if who == "starter" else who
    data = {"p": family, "f": progress.look(s, who), "lv": progress.starter_level(s),
            "ach": len(achievements.earned(s)), "pets": len(owned(s)), "won": s["fights_won"],
            "read": len((s.get("lessons") or {}).get("read", [])),
            "sk": [] if s["skills"] == "all" else sorted(s["skills"])}
    if name and NAME.fullmatch(name):
        data["n"] = name
    return data


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
    rows = [(_("Pet"), name), (_("Level"), str(data["lv"])), (_("Achievements"), str(data["ach"])),
            (_("Pets"), str(data["pets"])), (_("Fights won"), str(data["won"])),
            (_("Lessons read"), str(data["read"])),
            (_("Skills"), ", ".join(data["sk"]) or _("a bit of everything"))]
    if "n" in data:
        rows.insert(0, (_("Name"), data["n"]))
    return rows


# Upper bounds the page accepts (share.js reads them from share-pets.json).
BOUNDS = {"lv": (1, progress.MAX_LEVEL), "ach": (0, 999), "pets": (0, 99), "won": (0, 99999), "read": (0, 999)}


def page_data():
    """share-pets.json, published next to share.html: every family's forms and their sprites, the skills
    and the bounds. The page only draws what is listed here."""
    import json as _json
    from pathlib import Path
    from . import i18n, skills
    pets = Path(__file__).parent / "pets"
    fr = i18n.catalog("fr")
    families, sprites = {}, {}
    lines = [(line, list(forms), [FORM_NAMES[f] for f in forms]) for line, forms in STARTERS.items()]
    lines += [(pet, list(FORMS.get(pet, (pet,) * 3)[:len(STAGES[pet])]), list(STAGES[pet])) for pet, _n in ROSTER]
    for family, forms, names in lines:
        families[family] = {"forms": forms, "en": names, "fr": [fr.get(n) or n for n in names]}
        for sprite in forms:
            d = _json.loads((pets / f"{sprite}.json").read_text())
            sprites[sprite] = {"palette": d["palette"], "base": d["base"]}
    return {"families": families, "sprites": sprites, "skills": {k: v.split(":")[0] for k, v in skills.SKILLS.items()}, "bounds": BOUNDS}


def main(args):
    with state.locked() as s:
        if args.name is not None:
            if args.name and not NAME.fullmatch(args.name):
                print("  " + _("A name is 1 to 12 letters, digits, - or _ (no spaces): it shows on the image."))
                return 1
            s["share_name"] = args.name
        data = payload(s, s.get("share_name", ""))
    print("\n  " + BOLD + _("This is all your card shares:") + RESET)
    rows = describe(data)
    width = max(len(label) for label, _v in rows)
    for label, value in rows:
        print(f"    {label:<{width}}  {value}")
    print(f"  {DIM}" + _("No commands, files, machine names or dates. Change the name with bashou share --name NAME "
                         "(--name '' removes it).") + RESET + "\n")
    url = link(data)
    for line in qr.terminal(qr.encode(url)):
        print("  " + line)
    print("\n  " + _("Scan it with your phone: the page draws your banner, then Share sends it to Signal, "
                     "WhatsApp or any app.") )
    print(f"  {DIM}" + _("Your progress stays in the link, after the #: browsers never send that part to the "
                         "server.") + RESET)
    print(f"  {DIM}{url}{RESET}\n")
    return 0
