"""Logic fights: conditions in a shell script. `if`, `!` and `&&`/`||` read like English, and a single
flipped word lets the wrong people in. You fix the script, then `verify` runs it on every case."""

import json
import random
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from . import Challenge
from ..i18n import _
from .repos import EDITORS

GUESTS = ["alice", "bruno", "chloe", "dimitri", "emma", "farid", "giulia", "hugo", "ines", "jonas"]
STRANGERS = ["mallory", "trudy", "eve", "oscar"]
TRICKY = [".*", "a.*", "-v"]       # a regex or an option: the guard reads names as plain text (grep -F --)
FILES = ["notes.txt", "todo.txt", "journal.txt"]
FOLDERS = ["backup", "safe", "archive"]


def run(script, work, *args):
    """What the script prints, run with bash in `work` (empty when it hangs or bash is missing)."""
    try:
        done = subprocess.run(["bash", script.name, *args], cwd=work, stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout.strip()


# --- Negation Gnome: a `!` that turns the guard around ----------------------------------------------

DOOR = """#!/usr/bin/env bash
# The party door: only the guests written in guests.txt may come in.
# Usage: bash door.sh NAME
if ! grep -qxF -- "$1" guests.txt; then
  echo open
else
  echo closed
fi
"""


# A test to start from (owner): a case you know the answer to, run after every change. The player
# adds the next case; verify runs its own cases anyway.
DOOR_TEST = """#!/usr/bin/env bash
# A small test for door.sh. Run it: bash test_door.sh
# A test is a list of cases you already know the answer to. The test runs the script on each one and
# compares what it prints with what it should print. Programmers keep tests next to their code and run
# them after every change: a FAIL means the change broke something.

check() {{   # check NAME EXPECTED
  got=$(bash door.sh "$1")
  if [ "$got" = "$2" ]; then
    echo "ok    $1 -> $got"
  else
    echo "FAIL  $1 -> $got (expected $2)"
  fi
}}

check {guest} open      # {guest} is in guests.txt: the door must open

# Your turn: add a case for someone who is NOT on the list, like {stranger}. What must the door say?
"""


def door_setup(work, rng):
    guests = rng.sample(GUESTS, 4)
    stranger = rng.choice(STRANGERS)
    (work / "guests.txt").write_text("\n".join(guests) + "\n")
    (work / "door.sh").write_text(DOOR)
    (work / "test_door.sh").write_text(DOOR_TEST.format(guest=guests[0], stranger=stranger))
    return {"guests": guests, "args": {"guest": guests[0], "stranger": stranger}}


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
                and all(run(tmp / "door.sh", tmp, s) == "closed" for s in STRANGERS + TRICKY))


# --- Coin Wraith: heads OR tails, `||` where both conditions must hold ------------------------------------------------

SAVE = """#!/usr/bin/env bash
# Saves {file} into the folder {folder}/, but only when BOTH are there: the file and the folder.
if [ -f {file} ] || [ -d {folder} ]; then
  cp {file} {folder}/ && echo saved
else
  echo missing
fi
"""


SAVE_TEST = """#!/usr/bin/env bash
# A small test for save.sh. Run it: bash test_save.sh
# save.sh must say "saved" only when BOTH the file and the folder are there. So the test tries each
# case: it hides one of them, runs the script, then puts it back. A FAIL means the condition is wrong.

check() {{   # check EXPECTED CASE
  got=$(bash save.sh 2>/dev/null)
  if [ "$got" = "$1" ]; then
    echo "ok    $2 -> $got"
  else
    echo "FAIL  $2 -> $got (expected $1)"
  fi
}}

check saved "file and folder both there"

mv {folder} {folder}.hidden          # hide the folder...
check missing "no folder"
mv {folder}.hidden {folder}          # ...and put it back

# Your turn: hide the file instead (mv {file} {file}.hidden), check, then put it back.
"""


def save_setup(work, rng):
    file, folder = rng.choice(FILES), rng.choice(FOLDERS)
    (work / "save.sh").write_text(SAVE.format(file=file, folder=folder))
    (work / "test_save.sh").write_text(SAVE_TEST.format(file=file, folder=folder))
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

# --- Square Spider: a loop inside a loop, n × n comparisons ----------------------------------------------

BIG = 20000                # addresses in each hidden list
SMALL = 1000               # in the player's lists: slow enough to feel (a million comparisons)
LIMIT = 5                  # seconds verify gives the script on the hidden lists
FIRST = ["ana", "bo", "cy", "dee", "eli", "fay", "gus", "hal", "ivy", "jo", "kim", "lou", "max", "nia", "oto", "pia"]
# A dot in an address is any character to a regex (grep -F reads it as text), and bo@ hides inside
# jimbo@ (grep -x matches whole lines): the hidden lists hold both traps.
TRAPS = (["ana-b@example.org", "jimbo@example.org"], ["ana.b@example.org", "bo@example.org"])


def address_lists(rng, n):
    """Two lists of n addresses each (no repeats), about a third of them in both; shuffled."""
    pool = [f"{rng.choice(FIRST)}{k}@example.org" for k in rng.sample(range(10 * n, 100 * n), 2 * n - n // 3)]
    a, b = pool[:n], pool[n - n // 3:]
    rng.shuffle(a)
    rng.shuffle(b)
    return a, b


def big_lists(rng):
    a, b = address_lists(rng, BIG)
    a, b = a + TRAPS[0], b + TRAPS[1]
    rng.shuffle(a)
    rng.shuffle(b)
    return a, b


COMMON = """#!/usr/bin/env bash
# Prints the addresses found in both lists: customers.txt and newsletter.txt.
# Usage: bash common.sh
while IFS= read -r c; do
  while IFS= read -r m; do
    if [ "$c" = "$m" ]; then
      printf '%s\\n' "$c"
    fi
  done < newsletter.txt
done < customers.txt
"""

MISSING = """#!/usr/bin/env bash
# Prints who is missing: the addresses of team.txt that are not in present.txt.
# Usage: bash missing.sh
while IFS= read -r t; do
  found=no
  while IFS= read -r p; do
    if [ "$t" = "$p" ]; then
      found=yes
    fi
  done < present.txt
  if [ "$found" = no ]; then
    printf '%s\\n' "$t"
  fi
done < team.txt
"""

# The test handed to the player (owner: one case given, they add the next): right on a case you can
# check by eye, then timed on lists that double. n grows the time ×2, n × n grows it ×4.
SCALE_TEST = """#!/usr/bin/env bash
# A small test for {script}. Run it: bash test_{script}
# It works in a scratch folder, so your lists stay as they are.
#
# 1. Is it right? Three addresses in each list, checked by eye.
# 2. Is it fast? The same script on 200, 400, then 800 addresses. Each time the lists double:
#    if the time doubles too, the work grows like n. If it takes 4 times longer, it grows like n x n.
#    A fast script may not move at all: starting bash takes longer than the work.

tmp=$(mktemp -d) || exit 1
trap 'rm -rf -- "$tmp"' EXIT
cp {script} "$tmp/" || exit 1
cd "$tmp" || exit 1

printf '%s\\n' ana@example.org jimbo@example.org cy-d@example.org > {a}
printf '%s\\n' cy.d@example.org bo@example.org ana@example.org > {b}
got=$(bash {script} | sort | paste -sd ' ' -)
if [ "$got" = "{want}" ]; then
  echo "ok    {what}: $got"
else
  echo "FAIL  {what}: $got (expected {want})"
fi

TIMEFORMAT='%R s'
for n in 200 400 800; do     # Your turn: add 1600. How long would the old script take?
  seq -f 'user%g@example.org' "$n" > {a}
  seq -f 'user%g@example.org' 2 2 "$((2 * n))" > {b}
  printf '%s addresses: ' "$n"
  time bash {script} > out.txt
done
"""


def spaced(n):
    """20000 as 20 000, the way the hints and the lesson write it."""
    return f"{n:,}".replace(",", " ")


def scale_setup(script, text, a, b, want, what):
    def setup(work, rng):
        first, second = address_lists(rng, SMALL)
        (work / a).write_text("\n".join(first) + "\n")
        (work / b).write_text("\n".join(second) + "\n")
        (work / script).write_text(text)
        (work / f"test_{script}").write_text(SCALE_TEST.format(script=script, a=a, b=b, want=want, what=what))
        return {"seed": rng.randrange(10**6), "args": {"n": spaced(SMALL), "big": spaced(BIG), "limit": LIMIT}}
    return setup


_VERDICTS = {}             # (folder, script text) -> what the hidden run said: verify then why run it once


def scale_run(work, meta, script, hidden):
    """The script on the hidden files: "ok", "slow", "gone", or (lines it misses, lines it adds)."""
    path = Path(work) / script
    if not path.is_file():
        return "gone"
    text = path.read_text(errors="replace")
    key = (str(work), text)
    if key not in _VERDICTS:
        files, want = hidden(random.Random(meta["seed"]))
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / script).write_text(text)
            for name, lines in files.items():
                (tmp / name).write_text("\n".join(lines) + "\n")
            try:
                out = subprocess.run(["bash", script], cwd=tmp, stdin=subprocess.DEVNULL, capture_output=True,
                                     text=True, timeout=LIMIT).stdout
            except subprocess.TimeoutExpired:
                verdict = "slow"
            except OSError:
                verdict = "gone"
            else:
                got, want = Counter(out.splitlines()), Counter(want)
                verdict = "ok" if got == want else (sorted(want - got), sorted(got - want))
        _VERDICTS.clear()
        _VERDICTS[key] = verdict
    return _VERDICTS[key]


def scale_verify(*how):
    return lambda work, meta, value: scale_run(work, meta, *how) == "ok"


def scale_why(script, hidden, slow):
    def why(work):
        meta = json.loads((Path(work).parent / "meta.json").read_text())
        verdict = scale_run(work, meta, script, hidden)
        if verdict == "ok":
            return None
        if verdict == "gone":
            return _("{script} is gone: bash needs it to run.").format(script=script)
        if verdict == "slow":
            return slow().format(script=script, limit=LIMIT, big=spaced(BIG))
        misses, adds = verdict
        if adds:
            return _("Fast enough, but on the hidden files {script} prints {line}, and it shouldn't.").format(
                script=script, line=adds[0])
        return _("Fast enough, but on the hidden files {script} forgets {line}.").format(script=script, line=misses[0])
    return why


def lists(a, b, keep):
    """The hidden pair of address lists, saved as a and b; keep(first, second) is what the script must print."""
    def hidden(rng):
        first, second = big_lists(rng)
        return {a: first, b: second}, sorted(keep(first, second))
    return hidden


def slow_lists():
    return _("{script} didn't finish within {limit} seconds on the hidden lists of {big} addresses. Count the "
             "loops: how many times does the inner one run? A grep -f without -F counts too: each line of the list "
             "becomes a regex, tried on every line. So does a command run on every line: each start costs part of a "
             "millisecond, and they add up.")


SPIDER = ("common.sh", lists("customers.txt", "newsletter.txt", lambda a, b: set(a) & set(b)))
ROLL = ("missing.sh", lists("team.txt", "present.txt", lambda a, b: set(a) - set(b)))



# --- Parse Parrot: the same price list searched again on every line ----------------------------------------

ORDERS = BIG               # lines in the hidden orders
GOODS = ["tea", "cake", "jam", "bun", "pie", "soup", "rice", "fig"]
# tea-xl starts like tea: a table keyed on part of the name (or an unanchored search) mixes them up.
TWINS = ["tea", "tea-xl"]


def lookup_files(rng, n, items, row):
    """A table of `items` names (name, then a number) and n rows that use them; row(rng, k, item) -> a row."""
    names = [f"{rng.choice(GOODS)}{k}" for k in rng.sample(range(10 * items, 100 * items), items)]
    table = {name: rng.randrange(1, 400) for name in names}
    rows = [row(rng, k, rng.choice(names)) for k in range(n)]
    return table, rows


def with_twins(rng, table, rows, row):
    table.update({name: rng.randrange(1, 400) for name in TWINS})
    rows += [row(rng, len(rows) + k, name) for k, name in enumerate(TWINS * 20)]
    rng.shuffle(rows)
    return [f"{k} {v}" for k, v in table.items()], rows


def order(rng, k, item):
    return f"{rng.choice(FIRST)} {item} {rng.randrange(1, 9)}"


def pick(rng, k, item):
    return f"{1000 + k} {item}"


def bill_files(rng):
    table, rows = lookup_files(rng, ORDERS, ORDERS // 4, order)
    prices, rows = with_twins(rng, table, rows, order)
    want = [f"{c} {i} {table[i] * int(q)}" for c, i, q in (r.split() for r in rows)]
    return {"prices.txt": prices, "orders.txt": rows}, want


def shelf_files(rng):
    table, rows = lookup_files(rng, ORDERS, ORDERS // 4, pick)
    shelves, rows = with_twins(rng, table, rows, pick)
    want = [f"{o} {i} {table[i]}" for o, i in (r.split() for r in rows)]
    return {"shelves.txt": shelves, "picks.txt": rows}, want


BILL = """#!/usr/bin/env bash
# Prints the bill: for each order, who, what, and the price in cents.
# orders.txt: customer item quantity    prices.txt: item price_in_cents
# Usage: bash bill.sh
while read -r customer item qty; do
  price=$(grep "^$item " prices.txt | cut -d' ' -f2)
  printf '%s %s %s\\n' "$customer" "$item" "$((price * qty))"
done < orders.txt
"""

SHELF = """#!/usr/bin/env bash
# Prints where to pick each order: order, item, shelf number.
# picks.txt: order item    shelves.txt: item shelf
# Usage: bash shelf.sh
while read -r order item; do
  place=$(grep "^$item " shelves.txt | cut -d' ' -f2)
  printf '%s %s %s\\n' "$order" "$item" "$place"
done < picks.txt
"""

# The test handed to the player: right on a case checked by eye, then timed on files that double.
LOOKUP_TEST = """#!/usr/bin/env bash
# A small test for {script}. Run it: bash test_{script}
# It works in a scratch folder, so your files stay as they are.
#
# 1. Is it right? Three lines, checked by eye. tea-xl isn't tea.
# 2. Is it fast? The same script on 200, 400, then 800 lines. The time doubles: the work grows like n.
#    But divide: what does ONE line cost? Now multiply by 20 000.

tmp=$(mktemp -d) || exit 1
trap 'rm -rf -- "$tmp"' EXIT
cp {script} "$tmp/" || exit 1
cd "$tmp" || exit 1

printf '%s\\n' 'tea 250' 'tea-xl 400' 'cake 300' > {table}
printf '%s\\n' {case} > {rows}
got=$(bash {script} | sort | paste -sd , -)
if [ "$got" = "{want}" ]; then
  echo "ok    $got"
else
  echo "FAIL  $got (expected {want})"
fi

TIMEFORMAT='%R s'
for n in 200 400 800; do     # Your turn: add 1600.
  seq "$n" | sed 's/.*/item& 100/' > {table}
  seq "$n" | sed '{row}' > {rows}
  printf '%s lines: ' "$n"
  time bash {script} > out.txt
done
"""


def lookup_setup(script, text, table, rows, case, want, sed_row, make_row):
    """The player's files: a table of 250 items and 1 000 rows (a few seconds for the old script)."""
    def setup(work, rng):
        names, lines = with_twins(rng, *lookup_files(rng, SMALL, SMALL // 4, make_row), make_row)
        (work / table).write_text("\n".join(names) + "\n")
        (work / rows).write_text("\n".join(lines) + "\n")
        (work / script).write_text(text)
        (work / f"test_{script}").write_text(LOOKUP_TEST.format(script=script, table=table, rows=rows, case=case,
                                                                 want=want, row=sed_row))
        return {"seed": rng.randrange(10**6), "args": {"n": spaced(SMALL), "big": spaced(ORDERS), "limit": LIMIT}}
    return setup


def slow_orders():
    return _("{script} didn't finish within {limit} seconds on the hidden files of {big} lines. Count the programs "
             "it starts, and the times it reads the table: for every line?")


PARROT = ("bill.sh", bill_files)
SHELF_HOW = ("shelf.sh", shelf_files)


# --- Bitflip Banshee: Hamming(7,4), one parity check reads the wrong bits --------------------------------

# Positions 1 to 7: parity bits at 1, 2 and 4, data at 3, 5, 6 and 7. Check k covers the positions whose
# binary number includes k; the checks that fail, read as a binary number, give the position that flipped.
CHECKS = {1: (1, 3, 5, 7), 2: (2, 3, 6, 7), 4: (4, 5, 6, 7)}
BENDS = {1: (5, 6), 2: (6, 5), 4: (5, 3)}       # check: (position it should read, the one it reads instead)
DATA = (3, 5, 6, 7)
MESSAGES = ["OWL", "BITS", "SAFE", "FIXED", "ECHO", "BASH"]


def hamming(data):
    """The 7-bit word of 4 data bits: p1 p2 d1 p4 d2 d3 d4."""
    word = {pos: int(bit) for pos, bit in zip(DATA, data)}
    for k, covered in CHECKS.items():
        word[k] = sum(word[pos] for pos in covered if pos != k) % 2
    return "".join(str(word[pos]) for pos in range(1, 8))


def flip(word, pos):
    return word[:pos - 1] + "10"[int(word[pos - 1])] + word[pos:]


def hamming_cases():
    """Every message of 4 bits, sent clean and with each of its 7 bits flipped: (word, data)."""
    return [(flip(hamming(d), pos) if pos else hamming(d), d)
            for d in (format(n, "04b") for n in range(16)) for pos in range(8)]


def check_line(k, covered):
    return f"  s{k}=$(( " + " ^ ".join(f"b[{pos}]" for pos in covered) + " ))"


FIX_BITS = """#!/usr/bin/env bash
# Reads Hamming(7,4) words, one per line, fixes the bit that flipped, and prints the 4 data bits.
# A word is 7 bits, positions 1 to 7: parity bits at 1, 2 and 4, data bits at 3, 5, 6 and 7.
# Check k covers the positions whose binary number includes k (k = 1, 2, 4): s1 reads 1, 3, 5 and 7.
# Usage: bash fix_bits.sh < words.txt
status=0
while IFS= read -r word || [[ -n $word ]]; do
  if [[ ! $word =~ ^[01]{{7}}$ ]]; then
    printf 'not a 7-bit word: %s\\n' "$word" >&2
    status=1
    continue
  fi
  for i in 1 2 3 4 5 6 7; do
    b[i]=${{word:i-1:1}}
  done
{checks}
  bad=$(( s1 + 2 * s2 + 4 * s4 ))      # 0: no flip; else the position of the flipped bit
  if (( bad != 0 )); then
    b[bad]=$(( b[bad] ^ 1 ))
  fi
  printf '%s\\n' "${{b[3]}}${{b[5]}}${{b[6]}}${{b[7]}}"
done
exit "$status"
"""

ECC_TEST = """#!/usr/bin/env bash
# A small test for fix_bits.sh. Run it: bash test_fix_bits.sh
# Each case: a word as it arrived, and the 4 data bits that were sent.

fails=0
check() {{   # check WORD DATA
  local got
  got=$(printf '%s\\n' "$1" | bash fix_bits.sh)
  if [[ $got == "$2" ]]; then
    printf 'ok    %s -> %s\\n' "$1" "$got"
  else
    printf 'FAIL  %s -> %s (expected %s)\\n' "$1" "$got" "$2"
    fails=$(( fails + 1 ))
  fi
}}

check {clean} {clean_data}     # arrived clean
check {flipped} {flipped_data}     # bit {pos} flipped on the way

# Your turn: take {clean}, flip another bit, and check it gives {clean_data} back.

exit $(( fails > 0 ))
"""


def decode(word, checks):
    """What a decoder with these checks prints for a word."""
    b = {pos: int(bit) for pos, bit in enumerate(word, 1)}
    bad = sum(k * (sum(b[pos] for pos in covered) % 2) for k, covered in checks.items())
    if bad:
        b[bad] ^= 1
    return "".join(str(b[pos]) for pos in DATA)


def bent_checks(k):
    right, wrong = BENDS[k]
    return {**CHECKS, k: tuple(wrong if pos == right else pos for pos in CHECKS[k])}


def ecc_setup(work, rng):
    k = rng.choice(list(CHECKS))
    bent = bent_checks(k)
    (work / "fix_bits.sh").write_text(FIX_BITS.format(checks="\n".join(check_line(c, bent[c]) for c in bent)))
    cases = hamming_cases()
    clean = rng.choice([(w, d) for w, d in cases if w == hamming(d) and decode(w, bent) == d])
    flipped = rng.choice([(w, d) for w, d in cases if decode(w, bent) != d])
    pos = next(p for p in range(1, 8) if flip(flipped[0], p) == hamming(flipped[1]))
    (work / "test_fix_bits.sh").write_text(ECC_TEST.format(clean=clean[0], clean_data=clean[1], flipped=flipped[0],
                                                           flipped_data=flipped[1], pos=pos))
    message = rng.choice(MESSAGES)
    words = []
    for char in message:
        for nibble in (format(ord(char), "08b")[:4], format(ord(char), "08b")[4:]):
            spot = rng.randrange(8)
            words.append(flip(hamming(nibble), spot) if spot else hamming(nibble))
    (work / "words.txt").write_text("\n".join(words) + "\n")
    right, wrong = BENDS[k]
    return {"message": message, "args": {"k": k, "right": right, "wrong": wrong,
                                         "positions": ", ".join(map(str, CHECKS[k])),
                                         "line": check_line(k, CHECKS[k]).strip()}}


def feed(work, script, lines):
    """What `script` prints with these lines on its input, or None if it's gone or hangs."""
    path = Path(work) / script
    if not path.is_file():
        return None
    try:
        return subprocess.run(["bash", script], cwd=work, input="\n".join(lines) + "\n", capture_output=True,
                              text=True, timeout=10).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        return None


def ecc_wrong(work):
    """The first case fix_bits.sh gets wrong: (word, what it printed, data), "gone", or None."""
    cases = hamming_cases()
    got = feed(work, "fix_bits.sh", [w for w, d in cases])
    if got is None:
        return "gone"
    got += ["nothing"] * (len(cases) - len(got))
    return next(((w, g, d) for (w, d), g in zip(cases, got) if g != d), None)


def ecc_why(work):
    wrong = ecc_wrong(work)
    if wrong is None:
        return None
    if wrong == "gone":
        return _("fix_bits.sh is gone, or it never ends.")
    word, got, data = wrong
    return _("On {word}, fix_bits.sh prints {got}: the data sent was {data}.").format(word=word, got=got, data=data)


PARITY = """#!/usr/bin/env bash
# Checks bytes, one per line: 8 bits, the last one a parity bit that makes the number of 1s even.
# Prints ok, or flipped when the number of 1s is odd: a bit changed on the way (or 3, 5 or 7 of them).
# Usage: bash parity.sh < bytes.txt
status=0
while IFS= read -r byte || [[ -n $byte ]]; do
  if [[ ! $byte =~ ^[01]{8}$ ]]; then
    printf 'not an 8-bit byte: %s\\n' "$byte" >&2
    status=1
    continue
  fi
  p=0
  for (( i = 0; i < 8; i++ )); do
    p=$(( p | ${byte:i:1} ))
  done
  if (( p == 0 )); then
    echo ok
  else
    echo flipped
  fi
done
exit "$status"
"""

PARITY_TEST = """#!/usr/bin/env bash
# A small test for parity.sh. Run it: bash test_parity.sh

fails=0
check() {{   # check BYTE EXPECTED
  local got
  got=$(printf '%s\\n' "$1" | bash parity.sh)
  if [[ $got == "$2" ]]; then
    printf 'ok    %s -> %s\\n' "$1" "$got"
  else
    printf 'FAIL  %s -> %s (expected %s)\\n' "$1" "$got" "$2"
    fails=$(( fails + 1 ))
  fi
}}

check {clean} ok          # an even number of 1s
check {flipped} flipped     # one bit flipped: odd

# Your turn: add 11000000 (two 1s, even): it should say ok.

exit $(( fails > 0 ))
"""


def parity(bits):
    return str(bits.count("1") % 2)


def parity_cases():
    seven = [format(n, "07b") for n in range(0, 128, 9)]
    clean = [b + parity(b) for b in seven]
    return [(c, "ok") for c in clean] + [(flip(c, 1 + n % 8), "flipped") for n, c in enumerate(clean)]


def parity_setup(work, rng):
    (work / "parity.sh").write_text(PARITY)
    clean = rng.choice([c for c, w in parity_cases() if w == "ok" and c.count("1")])
    flipped = rng.choice([c for c, w in parity_cases() if w == "flipped" and c.count("1") > 1])
    (work / "test_parity.sh").write_text(PARITY_TEST.format(clean=clean, flipped=flipped))
    return {}


def parity_wrong(work):
    cases = parity_cases()
    got = feed(work, "parity.sh", [c for c, w in cases])
    if got is None:
        return "gone"
    got += ["nothing"] * (len(cases) - len(got))
    return next(((c, g, w) for (c, w), g in zip(cases, got) if g != w), None)


def parity_why(work):
    wrong = parity_wrong(work)
    if wrong is None:
        return None
    if wrong == "gone":
        return _("parity.sh is gone, or it never ends.")
    byte, got, want = wrong
    return _("On {byte}, parity.sh prints {got}: it should print {want}.").format(byte=byte, got=got, want=want)

ALL = [
    Challenge(level=1, id="negation_gnome", threat="Negation Gnome", **LOGIC,
              task="The Negation Gnome added one character to the party door, door.sh: now {guest} is left "
                   "outside and {stranger} walks in.\nFix door.sh so the guests of guests.txt get open and "
                   "everyone else gets closed. Try it with: bash door.sh {guest}. A small test is ready too: "
                   "bash test_door.sh, add your own case to it. Then: verify",
              hints=["Read the if line aloud. grep -q finds the name quietly: it succeeds when the name is on "
                     "the list. The ! in front turns that answer around, so the if now means \"if the name is "
                     "NOT on the list, open\". Then run bash door.sh {guest} and bash door.sh {stranger} to "
                     "see the difference.",
                     "Remove the ! (and its space) from the if line: `if grep -qxF -- \"$1\" guests.txt; then`. "
                     "Open it with {editor} door.sh, fix the line ({save_keys}). Or in one "
                     "command: sed -i 's/if ! grep/if grep/' door.sh"],
              setup=door_setup, verify=door_verify),
    Challenge(level=1, id="coin_wraith", threat="Coin Wraith", after=("negation_gnome",), **LOGIC,
              task="The Coin Wraith flipped one word in save.sh: it should save {file} into {folder}/ only when both "
                   "are there, but now heads or tails, one of them is enough, and cp fails.\nFix the "
                   "condition. A small test tries the cases for you: bash test_save.sh. Then: verify",
              hints=["|| means OR: the whole condition is true as soon as ONE side is true. && means AND: both "
                     "sides must be true. Here the script needs the file AND the folder. Try it: move the "
                     "folder away (mv {folder} gone), run bash save.sh, then put it back (mv gone {folder}).",
                     "On the if line, replace || with &&: `if [ -f {file} ] && [ -d {folder} ]; then`. With "
                     "{editor}: {editor} save.sh. Or in one command: sed -i 's/||/\\&\\&/' save.sh"],
              setup=save_setup, verify=save_verify),
    Challenge(level=2, id="square_spider", threat="Square Spider", after=("coin_wraith",), **LOGIC,
              task="The Square Spider spun its web inside common.sh. The script finds the addresses that are in both "
                   "customers.txt and newsletter.txt, and it's right, but it compares every customer with every "
                   "subscriber: {n} addresses already take seconds, and the real lists have {big}.\nMake it fast "
                   "and keep it right: verify runs it on two hidden lists of {big} addresses and gives it {limit} "
                   "seconds. Measure first: bash test_common.sh. Then: verify",
              hints=["Count the work. For each customer, the inner loop reads the whole newsletter: n customers "
                     "make n × n comparisons. 1 000 addresses: a million. 20 000: 400 million. bash test_common.sh "
                     "shows it: each time the lists double, the time is multiplied by 4.",
                     "Let one command read each file once: grep -Fxf newsletter.txt customers.txt prints the lines "
                     "of customers.txt that are also a line of newsletter.txt. -f reads what to look for from that "
                     "file, -F as plain text (a dot is just a dot, and grep stays fast), -x as whole lines (bo@example.org isn't "
                     "jimbo@example.org). Replace the two loops with it: {editor} common.sh ({save_keys}). Or in one "
                     "command: sed -i '/^while/,$d' common.sh && echo 'grep -Fxf newsletter.txt customers.txt' >> "
                     "common.sh (sed -i is GNU sed; on macOS: sed -i '' …). On macOS, grep -f with thousands of lines "
                     "is slow: use comm."
                     " grep's exit status becomes the script's: 1 just means no line printed, 2 is a real error (a missing list)."],
              setup=scale_setup("common.sh", COMMON, "customers.txt", "newsletter.txt", "ana@example.org",
                                "in both lists"),
              verify=scale_verify(*SPIDER), why=scale_why(*SPIDER, slow_lists)),
    Challenge(level=2, id="parse_parrot", threat="Parse Parrot", after=("square_spider",), **LOGIC,
              task="The Parse Parrot repeats itself: for each order of orders.txt, bill.sh searches prices.txt "
                   "again, from the top. Make it fast enough for {big} orders and keep it right: verify runs it "
                   "on hidden files and gives it {limit} seconds. Measure first: bash test_bill.sh. Then: verify",
              hints=["Count what one line costs. For every order, $( ) starts a new process, then grep and cut "
                     "start too, and grep reads prices.txt from the top: {n} orders, thousands of programs, and "
                     "the same file read {n} times. bash test_bill.sh shows it: the time only doubles with the "
                     "lines, but each line costs a millisecond or more.",
                     "Read prices.txt once, into a table: an associative array, item → price. Before the loop: "
                     "declare -A price, then while read -r item cents; do price[$item]=$cents; done < prices.txt. "
                     "In the loop, $((price[$item] * qty)) looks the price up without reading any file. Edit it: "
                     "{editor} bill.sh ({save_keys}). Or in two commands: sed -i -e '/^  price=/d' -e "
                     "'s/\\$((price \\* qty))/$((price[$item] * qty))/' bill.sh && sed -i '/^while/i declare -A "
                     "price; while read -r item cents; do price[$item]=$cents; done < prices.txt' bill.sh (GNU sed "
                     "only: on macOS, edit the file). (declare -A needs bash 4 or newer: on macOS, brew install bash.)"],
              setup=lookup_setup("bill.sh", BILL, "prices.txt", "orders.txt", "'ana tea 2' 'bo tea-xl 1' 'cy cake 3'",
                                 "ana tea 500,bo tea-xl 400,cy cake 900", "s/.*/ana item& 2/", order),
              verify=scale_verify(*PARROT), why=scale_why(*PARROT, slow_orders)),
    Challenge(level=2, id="bitflip_banshee", threat="Bitflip Banshee", after=("coin_wraith",), **LOGIC,
              task="The Bitflip Banshee flipped at most one bit in each word of words.txt. fix_bits.sh should "
                   "find that bit and flip it back, but one of its checks reads the wrong position. Find it with "
                   "the small test: bash test_fix_bits.sh. Fix it; verify then tries every possible word, sent "
                   "clean and with each of its 7 bits flipped. The fixed output, 4 bits per line, hides a word: "
                   "two lines make one letter.",
              hints=["Each check is an XOR, ^: 1 when an odd number of its bits are 1. Check k covers the "
                     "positions whose binary number includes k: 5 is 101 = 4 + 1, so s1 and s4 read it. So s{k} "
                     "must read positions {positions}. Compare "
                     "each s line with that rule: which one reads a position it shouldn't?",
                     "s{k} reads b[{wrong}] instead of b[{right}]. The line must be: {line}. Edit it: "
                     "{editor} fix_bits.sh ({save_keys}). Or: sed -i 's/^  s{k}=.*/  {line}/' fix_bits.sh "
                     "(GNU sed; on macOS: sed -i '' …). Then bash test_fix_bits.sh, and verify.",
                     "To read the word: bash fix_bits.sh < words.txt | paste -d '' - - | while IFS= read -r byte; "
                     "do printf '%b' \"\\\\x$(printf '%x' \"$((2#$byte))\")\"; done; echo. paste joins the lines two "
                     "by two into bytes, 2#… reads binary, %x writes it in hex, and \\x… prints that letter."],
              setup=ecc_setup, verify=lambda work, meta, value: ecc_wrong(work) is None,
              why=lambda work: ecc_why(work)),
]

# The Sage Owl's chest for the Logic path: the same flipped door, no enemy.
from .trials import trial  # noqa: E402

DOOR_CHEST = trial("trial_logic_door", 1, "A door script hides in this chest: door.sh. It lets strangers in and "
                   "keeps the guests of guests.txt out. Fix its condition, and try it with the small test: "
                   "bash test_door.sh. Then: verify",
                   ALL[0].hints, door_setup, door_verify, requires=["bash", "grep"], teaches=["if"])
# Its chest after the cost lesson: the same nested loops, for who is missing.
ROLL_CHEST = trial("trial_logic_missing", 2, "A roll-call script hides in this chest: missing.sh prints the "
                   "addresses of team.txt that aren't in present.txt, with a loop inside a loop. Make it fast "
                   "enough for two lists of 20 000 addresses (5 seconds) and keep it right: bash test_missing.sh. "
                   "Then: verify",
                   ["For each address of team.txt, the inner loop reads all of present.txt: n × n comparisons. "
                    "bash test_missing.sh shows the time multiplied by 4 each time the lists double.",
                    "grep -vFxf present.txt team.txt reads each file once: -f takes what to look for from "
                    "present.txt, -F as plain text (fast, and a dot is just a dot), -x as whole lines, and -v keeps the lines that DON'T match. "
                    "Or sorted: comm -23 <(sort team.txt) <(sort present.txt) keeps the lines only in the first. "
                    "Replace the loops with one of them in missing.sh. (On macOS, grep -f with thousands of lines is slow: use comm.)"
                    " grep's exit status becomes the script's: 1 just means no line printed, 2 is a real error (a missing list)."],
                   scale_setup("missing.sh", MISSING, "team.txt", "present.txt",
                               "cy-d@example.org jimbo@example.org", "missing"),
                   scale_verify(*ROLL), requires=["bash", "grep", "sort"], teaches=["comm"],
                   why=scale_why(*ROLL, slow_lists), file="")
# Its chest after the data lesson: the same search on every line, for a warehouse.
SHELF_CHEST = trial("trial_logic_shelf", 2, "A picking script hides in this chest: shelf.sh prints the shelf of "
                    "each order of picks.txt, and searches shelves.txt again for every line. Make it fast enough "
                    "for {big} orders ({limit} seconds) and keep it right: bash test_shelf.sh. Then: verify",
                    ["For every order, shelf.sh starts grep and cut and reads shelves.txt from the top: {n} orders, "
                     "{n} searches of the same file. bash test_shelf.sh shows what one line costs.",
                     "Read shelves.txt once, into a table: declare -A shelf, then while read -r item n; do "
                     "shelf[$item]=$n; done < shelves.txt, before the loop. In the loop, ${{shelf[$item]}} gives "
                     "the shelf without reading any file. (declare -A needs bash 4 or newer: on macOS, brew install "
                     "bash.) Or awk does both: awk 'NR == FNR {{ shelf[$1] = $2; next }} "
                     "{{ print $1, $2, shelf[$2] }}' shelves.txt picks.txt"],
                    lookup_setup("shelf.sh", SHELF, "shelves.txt", "picks.txt", "'7 tea' '8 tea-xl' '9 cake'",
                                 "7 tea 250,8 tea-xl 400,9 cake 300", "s/.*/& item&/", pick),
                    scale_verify(*SHELF_HOW), requires=["bash", "grep"], teaches=["declare"],
                    why=scale_why(*SHELF_HOW, slow_orders), file="")
# Its chest after the codes lesson: a parity bit, with | where ^ belongs.
PARITY_CHEST = trial("trial_logic_parity", 2, "A parity checker hides in this chest: parity.sh reads bytes whose "
                     "last bit makes the number of 1s even, and should say flipped when one bit changed. It says "
                     "flipped almost always. Try it: bash test_parity.sh. Fix it, then: verify",
                     ["The p= line uses |, an OR: 1 as soon as one bit is 1, so nearly every byte looks flipped. "
                      "Parity needs XOR, ^: 1 ^ 1 = 0, so p ends at 1 only when the number of 1s is odd.",
                      "Change | into ^ on the p= line: {editor} parity.sh ({save_keys}). Or: sed -i "
                      "'s/p | /p ^ /' parity.sh (GNU sed; on macOS: sed -i '' …). Then bash test_parity.sh."],
                     parity_setup, lambda work, meta, value: parity_wrong(work) is None, requires=["bash"],
                     teaches=["^"], why=lambda work: parity_why(work), file="")
CHESTS = [DOOR_CHEST, ROLL_CHEST, SHELF_CHEST, PARITY_CHEST]                    # locked chests in `bashou adventure`
