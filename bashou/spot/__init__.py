"""`bashou spot`: what is this string? (owner, 2026-10-02/03)

An IPv6, a hash, base64, a regex, a line of Rust… A string in the center, 4 answers on the arrow keys, 20
seconds for the whole game. The bag holds every kind twice; a good answer takes the string out, a
wrong one puts its kind back in the bag. No explanation: you go fast and learn from your mistakes, like
when you skim real logs and configs.
"""

import base64
import ipaddress
import random
import time
import uuid


GAME_SECONDS = 25                # owner: 20 good answers is the last star, 5 more seconds for it
COPIES = 2                       # each kind twice in the bag: it can come back
LONGEST, LABEL = 40, 14           # string and answer lengths: all on one line of 80 columns
GAP = 5                          # columns between the string and the answers on its sides
TIERS = [(5, "Quick eye"), (10, "Sharp eyes"), (15, "Hawk eyes"), (20, "Eagle eyes")]   # good answers in a game

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
        self.known = set()                     # kinds answered right in this game
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
            self.known.add(self.kind)
        else:
            self.mistakes += 1
            self.bag.insert(self.rng.randint(0, len(self.bag)), self.kind)
        self.last = (good, self.kind)
        self.next()


def tier(score):
    names = [name for need, name in TIERS if score >= need]
    return names[-1] if names else ""
