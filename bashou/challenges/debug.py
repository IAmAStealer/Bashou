"""Building and debugging C (owner, 2026-09-25: "gcc use and debugger use will need their lesson / hint / fights").

Two gcc fights (a file left out of the build, a bug only -Wall reports) and two gdb fights (find the
line that crashes with a backtrace, read a variable at a breakpoint). They build on the first C fight.
"""

import os
import tempfile

from . import Challenge
from .code import COMPILERS, NAMES, c_tests, header, run
from ..i18n import _


def fresh(work, name):
    """Your program, as you built it: it must exist and be newer than every source file."""
    prog = work / name
    if not prog.is_file() or not os.access(prog, os.X_OK):
        return None
    if any(src.stat().st_mtime > prog.stat().st_mtime for src in work.glob("*.[ch]")):
        return None
    return prog


def built_runs(name):
    """verify(): run the program you built on meta["runs"] ([args, expected stdout])."""
    def verify(work, meta, value):
        prog = fresh(work, name)
        if not prog:
            return False
        for args, expected in meta["runs"]:
            r = run([str(prog), *args], work)
            if not r or r.returncode != 0 or r.stdout != expected:
                return False
        return True
    return verify


# --- gcc: a file left out ---------------------------------------------------------

STATS_H = "#ifndef STATS_H\n#define STATS_H\n\ndouble mean(const int *values, int count);\n\n#endif\n"
STATS_C = """
#include "stats.h"

double mean(const int *values, int count)
{
    long total = 0;
    for (int i = 0; i < count; i++)
        total += values[i];
    return count ? (double)total / count : 0.0;
}
"""
REPORT_C = """
#include <stdio.h>
#include <stdlib.h>
#include "stats.h"

int main(int argc, char **argv)
{
    int values[64];
    int count = 0;
    for (int i = 1; i < argc && count < 64; i++)
        values[count++] = atoi(argv[i]);
    printf("mean: %.2f\\n", mean(values, count));
    return 0;
}
"""


def link_setup(work, rng):
    (work / "report.c").write_text(header("c", [
        _("Fight: gcc report.c -o report stops with: undefined reference to `mean'."),
        _("mean() is written in stats.c. The linker needs every file that holds a piece of the program."),
        _("Wanted: ./report 2 4 9 prints mean: 5.00"),
        _("Run it:") + " gcc report.c -o report && ./report 2 4 9",
        _("Help:") + " bashou explain c link",
    ]) + REPORT_C)
    (work / "stats.c").write_text(STATS_C.lstrip())
    (work / "stats.h").write_text(STATS_H)
    runs = []
    for _i in range(3):
        values = [rng.randint(1, 99) for _j in range(rng.randint(2, 6))]
        runs.append([[str(v) for v in values], f"mean: {sum(values) / len(values):.2f}\n"])
    return {"runs": [[["2", "4", "9"], "mean: 5.00\n"]] + runs}


# --- gcc: the warning that was a bug ------------------------------------------------

GRADE_C = """
#include <stdio.h>
#include <stdlib.h>

const char *grade(int score)
{
    if (score = 100)
        return "perfect";
    if (score >= {mark})
        return "pass";
    return "fail";
}

int main(int argc, char **argv)
{
    for (int i = 1; i < argc; i++)
        printf("%s\\n", grade(atoi(argv[i])));
    return 0;
}
"""


def grade_answer(score, mark):
    return "perfect" if score == 100 else "pass" if score >= mark else "fail"


def warning_setup(work, rng):
    mark = rng.randint(40, 60)
    (work / "grade.c").write_text(header("c", [
        _("Fight: gcc builds this without a word, yet every score comes out perfect."),
        _("Build it with warnings on: gcc -Wall grade.c -o grade. Read the warning, fix that line."),
        _("Wanted: 100 is perfect, {mark} or more is pass, less is fail.").format(mark=mark),
        _("Done when gcc -Wall says nothing and ./grade 100 {mark} 7 prints perfect, pass, fail.").format(mark=mark),
        _("Help:") + " bashou explain c warnings",
    ]) + GRADE_C.replace("{mark}", str(mark)))
    scores = [100, mark, mark - 1, 7, 99, rng.randint(0, 99)]
    return {"runs": [[[str(s) for s in scores], "", "".join(grade_answer(s, mark) + "\n" for s in scores)]],
            "args": {"mark": mark}}


def warning_verify(work, meta, value):
    """Your grade.c builds without a single warning under -Wall, and grades right."""
    with tempfile.TemporaryDirectory() as tmp:
        r = run(["gcc", "-Wall", "-Werror", str(work / "grade.c"), "-o", "prog"], tmp)
        if not r or r.returncode != 0:
            return False
    return c_tests("grade.c")(work, meta, value)


# --- gdb: where does it crash? ------------------------------------------------------

CRASH_C = """
#include <stdio.h>
#include <string.h>

struct setting {
    const char *key;
    const char *value;
};

static struct setting settings[] = {
    {"{a}", "on"},
    {"{b}", "42"},
    {"{c}", "/var/log"},
};

const char *lookup(const char *key)
{
    for (unsigned i = 0; i < sizeof settings / sizeof settings[0]; i++)
        if (strcmp(settings[i].key, key) == 0)
            return settings[i].value;
    return NULL;
}

int first_char(const char *key)
{
    const char *value = lookup(key);
    return value[0];                                   /* CRASH */
}

int check(const char *key)
{
    int c = first_char(key);
    return c != 0;
}

int main(void)
{
    int ok = 0;
    ok += check("{a}");
    ok += check("{b}");
    ok += check("{missing}");
    ok += check("{c}");
    printf("%d settings ok\\n", ok);
    return 0;
}
"""


def crash_setup(work, rng):
    a, b, c, missing = rng.sample(("color", "port", "logdir", "theme", "user", "timeout", "mode", "cache"), 4)
    code = CRASH_C.replace("{a}", a).replace("{b}", b).replace("{c}", c).replace("{missing}", missing)
    code = code.replace("                                   /* CRASH */", "")
    code = code.replace("int first_char", "\n" * rng.randint(0, 6) + "int first_char")   # the line moves
    text = header("c", [
        _("Fight: this program dies with 'Segmentation fault'. Don't fix it: find where it dies."),
        _("A debugger runs the program and stops right where it crashes."),
        _("Build it with -g (line numbers), run it in gdb, then ask for the backtrace: bt."),
        _("Run it:") + " gcc -g crash.c -o crash && gdb -q ./crash",
        _("Help:") + " bashou explain c gdb",
    ]) + code
    (work / "crash.c").write_text(text)
    line = next(i for i, l in enumerate(text.split("\n"), 1) if "return value[0];" in l)
    return {"answer": str(line)}


# --- gdb: a value at a breakpoint -----------------------------------------------------

LOAN_C = """
#include <stdio.h>

long month_end(int month, long balance)
{
    long interest = balance * {rate} / 1000;
    long paid = {pay} + month * {extra};
    return balance + interest - paid;
}

int main(void)
{
    long balance = {start};
    for (int month = 1; month <= 12; month++)
        balance = month_end(month, balance);
    printf("after a year: %ld\\n", balance);
    return 0;
}
"""


def loan_setup(work, rng):
    rate, pay, extra, start = rng.randint(7, 19), rng.randint(300, 700), rng.randint(3, 25), rng.randint(20, 90) * 1000
    month = rng.randint(4, 9)
    code = (LOAN_C.replace("{rate}", str(rate)).replace("{pay}", str(pay)).replace("{extra}", str(extra))
            .replace("{start}", str(start)))
    balance = start
    for m in range(1, month):
        balance = balance + balance * rate // 1000 - (pay + m * extra)
    (work / "loan.c").write_text(header("c", [
        _("Fight: what is balance when month_end() starts for month {month}? The program only prints the end.").format(
            month=month),
        _("Stop it there with a breakpoint, then print the variable."),
        _("Run it:") + " gcc -g loan.c -o loan && gdb -q ./loan",
        _("Help:") + " bashou explain c gdb",
    ]) + code)
    return {"answer": str(balance), "args": {"month": month}}


# --- the fights -----------------------------------------------------------------------

def gdb_used(analysis):
    return "gdb" in analysis.tools


C = dict(tools=COMPILERS, requires=["gcc"], skill="c", pet="beaver")
GDB = dict(tools=("gdb",), uses=gdb_used, requires=["gcc", "gdb"], skill="c", pet="beaver")

ALL = [
    Challenge(level=1, id="linker_lynx", fix=True, threat="Linker Lynx", after=("semicolon_slug",), **C,
              task="The Linker Lynx split report.c in two: gcc report.c -o report fails with "
                   "undefined reference to `mean'.\n"
                   "Build ./report from every file it needs, so ./report 2 4 9 prints mean: 5.00\n"
                   "When it works, type: verify",
              hints=["\"undefined reference\" comes from the linker, the last step of gcc: report.c calls mean(), "
                     "but the code of mean() is in stats.c, and gcc was only given report.c.",
                     "gcc takes several .c files at once and links them into one program (the .h file is only "
                     "read by #include, you don't list it).",
                     "Try: gcc report.c stats.c -o report && ./report 2 4 9"],
              setup=link_setup, verify=built_runs("report")),
    Challenge(level=2, id="warning_wraith", fix=True, threat="Warning Wraith", after=("linker_lynx",), **C,
              task="The Warning Wraith hides in grade.c: gcc builds it silently, and every score is perfect.\n"
                   "Build it with gcc -Wall grade.c -o grade, fix the line the warning points at, "
                   "until -Wall says nothing.\n"
                   "When it works, type: verify",
              hints=["-Wall turns on the warnings for the usual mistakes. Read the first one: file, line, and "
                     "what gcc finds suspicious.",
                     "= stores a value, == compares. if (score = 100) stores 100 in score, and 100 counts as "
                     "true: every score is \"perfect\".",
                     "Write if (score == 100), then: gcc -Wall grade.c -o grade && ./grade 100 {mark} 7"],
              setup=warning_setup, verify=warning_verify),
    Challenge(level=2, id="segfault_salamander", threat="Segfault Salamander", after=("semicolon_slug",), **GDB,
              task="The Segfault Salamander makes crash.c die with 'Segmentation fault'.\n"
                   "At which line of crash.c does it crash? Build it with -g, run it in gdb, "
                   "ask for the backtrace. Then: answer <line>",
              hints=["gcc -g adds line numbers to the program. In gdb, run starts it; when it crashes, gdb stops "
                     "and shows where. bt (backtrace) lists the calls, the one that crashed first: "
                     "bashou explain c gdb",
                     "The first line of bt says the function and crash.c:LINE. That number is the answer.",
                     "Try: gcc -g crash.c -o crash && gdb -q -batch -ex run -ex bt ./crash"],
              setup=crash_setup),
    Challenge(level=3, id="breakpoint_beetle", threat="Breakpoint Beetle", after=("segfault_salamander",), **GDB,
              task="The Breakpoint Beetle hides a number in loan.c: it only prints the balance after a year.\n"
                   "What is balance when month_end() starts for month {month}? Then: answer <number>",
              hints=["A breakpoint pauses the program at a function or a line. break month_end stops at every "
                     "call of month_end(); print balance shows the variable there: bashou explain c gdb",
                     "Stop only at the right call with a condition: break month_end if month == {month}. Then "
                     "run, then print balance.",
                     "Try: gcc -g loan.c -o loan && gdb -q -batch -ex 'break month_end if month == {month}' "
                     "-ex run -ex 'print balance' ./loan"],
              setup=loan_setup),
]


def chest_setup(work, rng):
    name = rng.choice(NAMES)
    code = ("#include <stdio.h>\n\nint count(const char *s)\n{\n    int n = 0;\n    while (*s++)\n        n++;\n"
            "    return n;\n}\n\nint main(void)\n{\n    const char *names[] = {\"" + name + "\", 0};\n"
            "    for (int i = 0; i < 2; i++)\n        printf(\"%d\\n\", count(names[i]));\n    return 0;\n}\n")
    (work / "count.c").write_text(code)
    line = next(i for i, l in enumerate(code.split("\n"), 1) if "while (*s++)" in l)
    return {"answer": str(line)}


def trial():
    from .trials import trial as make
    return make("trial_gdb_line", 2, "count.c crashes. Build it with gcc -g, run it in gdb and ask bt: at which line "
                "of count.c does it stop? Then: answer <line>",
                ["gcc -g count.c -o count builds it with line numbers. In gdb: run, then bt.",
                 "Try: gcc -g count.c -o count && gdb -q -batch -ex run -ex bt ./count"],
                chest_setup, lambda w, m, v: v.strip() == m["answer"], requires=["gcc", "gdb"], teaches=["gdb"])


CHEST = trial()
