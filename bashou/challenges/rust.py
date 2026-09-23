"""Rust fights (owner, 2026-09-23): first steps with variables, only where rustc is installed.

One file, built with `rustc` (no cargo project needed). Like the C fights, the file starts with a
comment saying what it must print, how to run it and which `bashou explain rust …` note helps; Bashou
then builds your version and compares what it prints.
"""

import os
import tempfile

from . import Challenge
from .code import NAMES, run
from ..i18n import _

PROGRAMS = {"counter", "points", "guess", "temps"}      # what the fights build (./counter is "counter")


def header(lines):
    lines = lines + [_("When it works, type: answer done")]
    return "".join("// " + line + "\n" for line in lines)


def write(work, name, lines, code):
    (work / name).write_text(header(lines) + code)


def rust_output(name):
    """verify(): build your file with rustc (a debug build: overflows panic), compare what it prints."""
    def verify(work, meta, value):
        with tempfile.TemporaryDirectory() as tmp:
            built = run(["rustc", "--edition", "2021", str(work / name), "-o", "prog"], tmp, timeout=120)
            if not built or built.returncode != 0:
                return False
            r = run(["./prog"], tmp, env={**os.environ, "RUST_BACKTRACE": "0"})
            return bool(r) and r.returncode == 0 and r.stdout == meta["expected"]
    return verify


def rust_used(analysis):
    return bool(analysis.tools & ({"rustc", "cargo"} | PROGRAMS))


COUNTER_CODE = '''
fn main() {{
    let lines = [{lines}];
    let errors = 0;
    for line in lines {{
        if line == "error" {{
            errors += 1;
        }}
    }}
    println!("{{}} errors", errors);
}}
'''


def counter_setup(work, rng):
    lines = [rng.choice(("ok", "error", "ok")) for _i in range(rng.randint(6, 10))]
    write(work, "counter.rs", [
        _("Fight: count the \"error\" lines. rustc refuses: a variable that changes must say so."),
        _("Wanted: one line, like: 3 errors"),
        _("Run it:") + " rustc counter.rs && ./counter",
        _("Help:") + " bashou explain rust mut",
    ], COUNTER_CODE.format(lines=", ".join(f'"{x}"' for x in lines)))
    return {"expected": f"{lines.count('error')} errors\n"}


POINTS_CODE = '''
const MAX_POINTS = {top};

fn main() {{
    let score = {score};
    println!("{{}} / {{}}", score, MAX_POINTS);
}}
'''


def points_setup(work, rng):
    top = rng.choice((100, 500, 1000))
    score = rng.randint(1, top)
    write(work, "points.rs", [
        _("Fight: a constant must say its type; a let can guess it."),
        _("Wanted: the score out of the maximum, like: 73 / 100"),
        _("Run it:") + " rustc points.rs && ./points",
        _("Help:") + " bashou explain rust const",
    ], POINTS_CODE.format(top=top, score=score))
    return {"expected": f"{score} / {top}\n"}


GUESS_CODE = '''
fn main() {{
    let mut guess = "  {n}  ";
    guess = guess.trim().parse().unwrap();
    println!("{{}}", guess * 2);
}}
'''


def guess_setup(work, rng):
    n = rng.randint(10, 99)
    write(work, "guess.rs", [
        _("Fight: guess starts as text and should become a number. mut can't change a type."),
        _("Wanted: the number doubled, like: 84 for \"  42  \""),
        _("Run it:") + " rustc guess.rs && ./guess",
        _("Help:") + " bashou explain rust shadowing",
    ], GUESS_CODE.format(n=n))
    return {"expected": f"{n * 2}\n"}


TEMPS_CODE = '''
fn main() {{
    let readings: [u8; 4] = [{readings}];
    let mut total: u8 = 0;
    for r in readings {{
        total += r;
    }}
    println!("{{}}", total / 4);
}}
'''


def temps_setup(work, rng):
    readings = [rng.randint(90, 250) for _i in range(4)]
    write(work, "temps.rs", [
        _("Fight: it builds, then panics: 'attempt to add with overflow'. A u8 stops at 255."),
        _("Wanted: the average of the 4 readings, rounded down."),
        _("Run it:") + " rustc temps.rs && ./temps",
        _("Help:") + " bashou explain rust integers",
    ], TEMPS_CODE.format(readings=", ".join(map(str, readings))))
    return {"expected": f"{sum(readings) // 4}\n"}


RUST = dict(tools=("rustc", "cargo"), uses=rust_used, requires=["rustc"], skill="rust")

ALL = [
    Challenge(level=1, id="mut_marmot", pet="beaver", threat="Mut Marmot", **RUST,
              task="The Mut Marmot froze a counter in counter.rs: rustc won't let it change.\n"
                   "Fix counter.rs (its first lines say what it must do). Run it: rustc counter.rs && ./counter\n"
                   "When it works, type: answer done",
              hints=["Read rustc's error: it names the variable and even suggests the fix. "
                     "bashou explain rust mut",
                     "Write: let mut errors = 0;"],
              setup=counter_setup, verify=rust_output("counter.rs")),
    Challenge(level=1, id="const_condor", pet="beaver", threat="Const Condor", **RUST,
              task="The Const Condor stole a type from points.rs: rustc stops at the constant.\n"
                   "Fix points.rs (its first lines say what it must do). Run it: rustc points.rs && ./points\n"
                   "When it works, type: answer done",
              hints=["A const always says its type after its name, like a function argument. "
                     "bashou explain rust const",
                     "Write: const MAX_POINTS: u32 = …;"],
              setup=points_setup, verify=rust_output("points.rs")),
    Challenge(level=2, id="shadow_shade", pet="beaver", threat="Shadow Shade", after=("mut_marmot",), **RUST,
              task="The Shadow Shade wants guess.rs to turn text into a number, and mut isn't enough.\n"
                   "Fix guess.rs (its first lines say what it must do). Run it: rustc guess.rs && ./guess\n"
                   "When it works, type: answer done",
              hints=["mut lets a value change, never its type. A new let with the same name can: "
                     "that's shadowing. bashou explain rust shadowing",
                     "Write: let guess = \"  42  \"; then let guess: u32 = guess.trim().parse().unwrap();"],
              setup=guess_setup, verify=rust_output("guess.rs")),
    Challenge(level=2, id="byte_basilisk", pet="beaver", threat="Byte Basilisk", after=("mut_marmot",), **RUST,
              task="The Byte Basilisk squeezes four readings into one byte in temps.rs.\n"
                   "Fix temps.rs (its first lines say what it must do). Run it: rustc temps.rs && ./temps\n"
                   "When it works, type: answer done",
              hints=["The readings fit in a u8, their sum doesn't. Give the total a bigger type. "
                     "bashou explain rust integers",
                     "Write: let mut total: u32 = 0; and total += r as u32;"],
              setup=temps_setup, verify=rust_output("temps.rs")),
]
