"""`bashou spot`: what is this string? (owner, 2026-10-02/03)

An IPv6, a hash, base64, a regex, a line of Rust… A string in the center, 4 answers on the arrow keys, 20
seconds for the whole game. The bag holds every kind twice; a good answer takes the string out, a
wrong one puts its kind back in the bag. No explanation: you go fast and learn from your mistakes, like
when you skim real logs and configs.
"""

import base64
import ipaddress
import os
import random
import re
import sys
import time
import uuid

from . import state, terminal
from .i18n import _
from .render import BOLD, DIM, ESC, RESET

GAME_SECONDS = 20
COPIES = 2                       # each kind twice in the bag: it can come back
LONGEST, LABEL = 40, 14           # string and answer lengths: all on one line of 80 columns
GAP = 5                          # columns between the string and the answers on its sides
GOOD, BAD, GOLD = "\033[38;2;120;200;120m", "\033[38;2;230;110;100m", "\033[38;2;240;200;90m"
TIERS = [(10, "Sharp eyes"), (20, "Hawk eyes"), (30, "Eagle eyes")]     # good answers in one game

WORDS = ["cat", "data", "home", "user", "log", "mail", "shop", "blue", "cloud", "pixel", "river", "stone",
         "night", "admin", "build", "test", "alpha", "delta", "nova", "tux"]
TLDS = ["com", "org", "net", "fr", "io", "dev", "eu"]


def ipv4(rng):
    return ".".join(str(rng.randint(1, 254)) for _ in range(4))


def ipv6(rng):
    """A real-looking address in its canonical form (RFC 5952: lowercase, no leading zeros, :: only for the
    longest run of zero groups): link-local fe80::/64, or global (2000::/3) with a 64-bit interface id."""
    iid = rng.getrandbits(64)
    if rng.random() < 0.4:
        value = (0xfe80 << 112) | iid
    else:
        prefix = rng.choice([0x2001, 0x2a01, 0x2a02, 0x2600, 0x2c0f])
        site = rng.getrandbits(48) if rng.random() < 0.6 else rng.getrandbits(16) << 32   # some with zero groups
        value = (prefix << 112) | (site << 64) | (iid if rng.random() < 0.7 else rng.randint(1, 0xffff))
    return str(ipaddress.IPv6Address(value))


def mac(rng):
    sep = rng.choice([":", "-"])
    return sep.join(f"{rng.randint(0, 255):02x}" for _ in range(6))


def uuid4(rng):
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def b64(rng):
    text = " ".join(rng.choice(WORDS) for _ in range(rng.randint(2, 5)))
    return base64.b64encode(text.encode()).decode()


def hexa(rng):
    raw = "".join(rng.choice("0123456789abcdef") for _ in range(rng.choice([4, 6, 8, 12])))
    return rng.choice([f"0x{raw}", " ".join(raw[i:i + 2] for i in range(0, len(raw), 2))])


def md5(rng):
    return "".join(rng.choice("0123456789abcdef") for _ in range(32))


def sha1(rng):
    """40 hex digits: a SHA-1, like a git commit id."""
    return "".join(rng.choice("0123456789abcdef") for _ in range(40))


def encrypted(rng):
    """openssl enc: "Salted__" then the salt and the ciphertext, in base64: it always starts with U2FsdGVkX1."""
    return base64.b64encode(b"Salted__" + bytes(rng.getrandbits(8) for _ in range(rng.choice([10, 16, 22])))).decode()


def jwt(rng):
    def part(data):
        return base64.urlsafe_b64encode(data.encode()).decode().rstrip("=")
    head, body = part('{"alg":"HS256"}'), part('{"id":%d}' % rng.randint(1, 99))
    sig = base64.urlsafe_b64encode(bytes(rng.getrandbits(8) for _ in range(4))).decode().rstrip("=")
    return f"{head}.{body}.{sig}"                                  # eyJ….eyJ….…: easy to spot


def basic_auth(rng):
    """An HTTP header's value: "Basic", then user:password in base64 (readable by anyone: not a secret)."""
    pair = f"{rng.choice(WORDS)}:{rng.choice(WORDS)}{rng.randint(1, 99)}"
    return "Basic " + base64.b64encode(pair.encode()).decode()


def email(rng):
    return f"{rng.choice(WORDS)}{rng.choice(['', '.', '_'])}{rng.choice(WORDS)}@{rng.choice(WORDS)}.{rng.choice(TLDS)}"


def url(rng):
    path = "/".join(rng.choice(WORDS) for _ in range(rng.randint(1, 2)))
    query = rng.choice(["", f"?id={rng.randint(1, 99)}", f"?q={rng.choice(WORDS)}"])
    return f"{rng.choice(['https', 'http'])}://{rng.choice(['www.', ''])}{rng.choice(WORDS)}.{rng.choice(TLDS)}/{path}{query}"


def iso_date(rng):
    d = f"{rng.randint(2015, 2030)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
    return rng.choice([d, f"{d}T{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:{rng.randint(0, 59):02d}Z"])


def timestamp(rng):
    return str(rng.randint(1_400_000_000, 1_900_000_000))


def pick(lines):
    return lambda rng: rng.choice(lines)


REGEXES = [r"^[a-z0-9._]+@\w+\.com$", r"\d{3}-\d{4}", r"(cat|dog)s?", r"^\s*#", r"[A-Z]{2,}\b", r"^\d+$",
           r"colou?r", r"[^aeiou]+", r"^(GET|POST) /\S*", r"\bfoo\b.*\bbar\b", r"[0-9a-f]{8}", r"^$"]
PYTHON = ["for name in names: print(name)", "def add(a, b): return a + b", "import os, sys",
          "with open(path) as f: data = f.read()", "if __name__ == \"__main__\":", "squares = [x * x for x in range(10)]",
          "print(f\"Hello {name}\")", "except ValueError as e:"]
RUST = ["fn main() { println!(\"hi\"); }", "let mut v: Vec<i32> = Vec::new();", "match cmd { Some(x) => x, None => 0 }",
        "use std::collections::HashMap;", "impl Display for Point {", "let s = String::from(\"tux\");",
        "fn len(s: &str) -> usize {", "#[derive(Debug, Clone)]"]
C = ["#include <stdio.h>", "int main(void) { return 0; }", "char *p = malloc(n * sizeof *p);",
     "printf(\"%d\\n\", count);", "for (int i = 0; i < n; i++) {", "struct node *next;", "free(buf); buf = NULL;",
     "if (fp == NULL) { perror(\"fopen\"); }"]
BASH = ["for f in *.txt; do echo \"$f\"; done", "if [[ -f $file ]]; then", "grep -rn TODO . | wc -l",
        "#!/usr/bin/env bash", "name=${1:-world}", "while read -r line; do", "echo \"$(date +%F)\" >> log",
        "[ $# -eq 0 ] && exit 1"]
SQL = ["SELECT name FROM users WHERE id = 3;", "INSERT INTO logs VALUES ('ok');", "UPDATE items SET qty = 0;",
       "CREATE TABLE notes (id INTEGER);", "SELECT count(*) FROM t GROUP BY day;",
       "DELETE FROM sessions WHERE age > 30;", "SELECT * FROM a JOIN b ON a.id = b.id;", "ALTER TABLE t ADD c TEXT;"]

# kind -> (label, family, generator). The wrong answers come from the same family first: close ones.
KINDS = {
    "ipv4": ("IPv4", "net", ipv4), "ipv6": ("IPv6", "net", ipv6), "mac": ("MAC address", "net", mac),
    "uuid": ("UUID", "net", uuid4),
    "base64": ("Base64", "code", b64), "hex": ("Hexadecimal", "code", hexa), "md5": ("MD5 hash", "code", md5),
    "sha1": ("SHA-1 hash", "code", sha1), "encrypted": ("Encrypted", "code", encrypted),
    "jwt": ("JWT token", "code", jwt), "basic": ("Basic auth", "code", basic_auth),
    "email": ("Email", "text", email), "url": ("URL", "text", url), "regex": ("Regex", "text", pick(REGEXES)),
    "date": ("ISO 8601 date", "text", iso_date), "timestamp": ("Unix timestamp", "text", timestamp),
    "python": ("Python", "lang", pick(PYTHON)), "rust": ("Rust", "lang", pick(RUST)), "c": ("C", "lang", pick(C)),
    "bash": ("Bash", "lang", pick(BASH)), "sql": ("SQL", "lang", pick(SQL)),
}
ARROWS = ["up", "left", "right", "down"]


def choices(kind, rng):
    """4 answers in arrow order: the right one, and 3 wrong ones (from its family first)."""
    family = KINDS[kind][1]
    near = [k for k in KINDS if k != kind and KINDS[k][1] == family]
    far = [k for k in KINDS if k != kind and KINDS[k][1] != family]
    wrong = rng.sample(near, min(3, len(near)))
    wrong += rng.sample(far, 3 - len(wrong))
    answers = [kind] + wrong
    rng.shuffle(answers)
    return answers


class Game:
    """The rules, without the screen: a bag, a clock, a score."""

    def __init__(self, rng=None, clock=time.monotonic):
        self.rng = rng or random.Random()
        self.clock = clock
        self.bag = [k for k in KINDS for _ in range(COPIES)]
        self.rng.shuffle(self.bag)
        self.score = self.mistakes = 0
        self.start = clock()
        self.last = None                       # (good?, kind) of the last answer, for a short flash
        self.next()

    def left(self):
        return max(0.0, GAME_SECONDS - (self.clock() - self.start))

    def over(self):
        return self.left() <= 0 or not self.bag and self.kind is None

    def next(self):
        if not self.bag:
            self.kind = None
            return
        self.kind = self.bag.pop()
        self.text = KINDS[self.kind][2](self.rng)
        self.answers = choices(self.kind, self.rng)

    def answer(self, arrow):
        """A key: "up", "down", "left" or "right". A wrong answer puts the kind back, somewhere in the bag."""
        if self.over() or arrow not in ARROWS:
            return
        chosen = self.answers[ARROWS.index(arrow)]
        good = chosen == self.kind
        if good:
            self.score += 1
        else:
            self.mistakes += 1
            self.bag.insert(self.rng.randint(0, len(self.bag)), self.kind)
        self.last = (good, self.kind)
        self.next()


def tier(score):
    names = [name for need, name in TIERS if score >= need]
    return names[-1] if names else ""


def center(text, cols):
    return " " * max(0, (cols - len(text)) // 2) + text


def layout(game, cols, rows):
    """Where everything goes, as (row, column, text, style), rows and columns from 1. The clock at the
    very top; the string exactly in the middle with its 4 answers around it and room to breathe
    (owner: nothing else near it, or it bothers you)."""
    left = game.left()
    bar_w = max(10, cols - 24)
    full = round(bar_w * left / GAME_SECONDS)
    mark, color = ("✔", GOOD) if game.last and game.last[0] else ("✗", BAD) if game.last else ("", "")
    parts = [(1, 2, "█" * full, ""), (1, 2 + full, "░" * (bar_w - full), DIM), (1, bar_w + 4, f"{left:4.1f} s", BOLD),
             (1, cols - 5, f"{game.score:>3}", BOLD)]
    mid, middle = rows // 2 + 1, cols // 2 + 1
    up, lft, rgt, down = (_(KINDS[k][0]) for k in game.answers)
    text = game.text
    parts += [(mid, middle - len(text) // 2, text, BOLD),
              (mid - 5, middle, mark, color),                    # right or wrong, just above the answers
              (mid - 3, middle - (len(up) + 2) // 2, f"↑ {up}", ""),
              (mid + 3, middle - (len(down) + 2) // 2, f"↓ {down}", ""),
              (mid, middle - len(text) // 2 - GAP - len(lft) - 2, f"← {lft}", ""),     # close to the string
              (mid, middle - len(text) // 2 + len(text) + GAP, f"{rgt} →", ""),
              (rows, 2, _("r: restart · q: quit"), DIM)]
    return parts


def draw(game, cols, rows):
    """One frame: the screen cleared, then each piece where `layout` puts it."""
    return f"{ESC}[H{ESC}[2J" + "".join(f"{ESC}[{r};{c}H{style}{text}{RESET if style else ''}"
                                         for r, c, text, style in layout(game, cols, rows) if text)


def save(score):
    """The best score and the games played. Returns (best before this game, best now)."""
    with state.locked() as s:
        spot = s["spot"]
        before = spot["best"]
        spot["best"] = max(before, score)
        spot["games"] += 1
        return before, spot["best"]


def end_screen(game, best_before, cols, rows):
    lines = [_("Time's up!") if game.left() <= 0 else _("The bag is empty!"), "",
             f"{BOLD}{_('Score')} {game.score}{RESET}  ·  " + _("{n} mistakes").format(n=game.mistakes)]
    if game.score > best_before:
        lines.append(GOLD + _("New best score!") + RESET)
    else:
        lines.append(DIM + _("Best: {best}").format(best=best_before) + RESET)
    name = tier(game.score)
    if name:
        lines.append(GOLD + "★ " + _(name) + RESET)
    nxt = next((need for need, _name in TIERS if game.score < need), None)
    if nxt:
        lines.append(DIM + _("{n} good answers for the next star").format(n=nxt) + RESET)
    lines += ["", DIM + _("Enter or r: play again · q: quit") + RESET]
    top = max(0, (rows - len(lines)) // 2)
    out = [center(line, cols + (len(line) - visible_len(line))) for line in lines]
    return f"{ESC}[H{ESC}[2J" + "\n" * top + "\n".join(out)


def visible_len(text):
    return len(re.sub(r"\x1b\[[0-9;]*m", "", text))


KEYS = {"r": "restart"}


def play(screen, cols, rows):
    """One game. Returns its Game, "restart" (r: a new game at once, this one not counted) or None (q)."""
    game = Game()
    while not game.over():
        sys.stdout.write(draw(game, cols, rows))
        sys.stdout.flush()
        for key in screen.keys(0.1):
            k = terminal.name(key, KEYS)
            if k == "quit":
                return None
            if k == "restart":
                return k
            game.answer(k)
    return game


def main():
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("  " + _("`bashou spot` is a game for your terminal: run it there."))
        return 1
    cols, rows = os.get_terminal_size()
    with terminal.Screen() as screen:
        while True:
            game = play(screen, cols, rows)
            if game is None:
                return 0
            if game == "restart":
                continue
            before, _best = save(game.score)
            sys.stdout.write(end_screen(game, before, cols, rows))
            sys.stdout.flush()
            time.sleep(0.6)                    # a last arrow pressed in a hurry doesn't skip the result
            screen.keys(0)
            while True:
                keys = [terminal.name(k, KEYS) for k in screen.keys(1)]
                if "quit" in keys:
                    return 0
                if "enter" in keys or "restart" in keys:
                    break
