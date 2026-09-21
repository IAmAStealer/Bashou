"""The arena: a bash sub-shell in a sandbox folder where you beat a threat with a real tool.

`bashou fight` runs `run()`. Inside the arena, the shell functions `answer`, `hint` and
`task` call back into this module (`python3 -m bashou.fight answer <base> <value>`).
"""

import datetime
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import challenges, progress, state
from .analyze import analyze, parse_log
from .i18n import _

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"
ACCENT, GOOD, BAD = "\033[38;2;150;190;230m", "\033[38;2;130;210;120m", "\033[38;2;240;110;110m"
WIN, FLEE = 42, 3          # exit codes of the arena shell (Ctrl-D is a flee)
THREAT_MINUTES = 30

RC = r"""
[[ -f ~/.bash_aliases ]] && source ~/.bash_aliases
PS1='\[\e[38;2;240;110;110m\]⚔ arena\[\e[0m\] \W \$ '
HISTFILE=$BASHOU_ARENA/history
_arena_log() {
  local s=$?
  if [[ -n $_arena_hc && $HISTCMD != "$_arena_hc" ]]; then
    printf '%s\t' "$s" >> "$BASHOU_ARENA/log"
    HISTTIMEFORMAT= history 1 >> "$BASHOU_ARENA/log"
  fi
  _arena_hc=$HISTCMD
  return "$s"
}
PROMPT_COMMAND=_arena_log
_arena() { PYTHONPATH=$BASHOU_SRC python3 -m bashou.fight "$@" "$BASHOU_ARENA"; }
answer() { _arena answer "$*" && exit 42; }
hint() { _arena hint; }
task() { _arena task; }
flee() { exit 3; }
cd "$BASHOU_ARENA/arena"
"""


# --- threats ---------------------------------------------------------------

def level(s):
    return (len(s["pets"]) + sum(progress.stage(s, p) - 1 for p in s["pets"])
            + progress.starter_level(s) - 1)


def remaining(s):
    return [c for c in challenges.ALL if c.id not in s["challenges"] and c.available()]


def threats_per_day(s):
    """About 3 a day at first, 1 later, fewer when the bank runs low, none when it's empty."""
    return max(1, min(3, 3 - level(s) // 3)) * min(1, len(remaining(s)) / 5)


def active_threat(s, now=None):
    t = s.get("threat")
    if t and t["until"] > (now or time.time()):
        return t
    return None


def maybe_threat(s, rng=random, now=None):
    """Called under the lock from the companion. Returns a notification or None."""
    now = now or time.time()
    if s.get("threat") and s["threat"]["until"] <= now:
        s["threat"] = None                                 # it left
    if s.get("threat"):
        return None
    today = datetime.date.fromtimestamp(now).isoformat()
    if s["threat_day"]["date"] != today:
        s["threat_day"] = {"date": today, "count": 0}
    if s["threat_day"]["count"] >= threats_per_day(s) or now - s["last_threat"] < 2 * 3600:
        return None
    pool = remaining(s)
    if not pool or rng.random() > 1 / 120:                 # one chance in 120 per 30 s at the prompt
        return None
    ch = rng.choice(pool)
    s["threat"] = {"challenge": ch.id, "until": now + THREAT_MINUTES * 60}
    s["threat_day"]["count"] += 1
    s["last_threat"] = now
    return announcement(s, now)


def announcement(s, now=None):
    """What the pet says about the waiting threat, or None."""
    t = active_threat(s, now)
    if not t or t["challenge"] not in challenges.BY_ID:
        return None
    ch = challenges.BY_ID[t["challenge"]]
    return "⚠ " + _("A {threat} is coming! Use `{tool}` to fight it → bashou fight").format(
        threat=_(ch.threat), tool=ch.tool)


def gone(challenge_id):
    """What the pet says when a threat got tired of waiting."""
    ch = challenges.BY_ID.get(challenge_id)
    name = _(ch.threat) if ch else "?"
    return "💨 " + _("The {threat} got tired of waiting and left. It'll be back!").format(threat=name)


# --- arena -----------------------------------------------------------------

def pick(s):
    """The challenge of the threat your pet announced, or None: no threat, no fight."""
    t = active_threat(s)
    if t and t["challenge"] in challenges.BY_ID:
        return challenges.BY_ID[t["challenge"]]
    return None


def load_meta(base):
    return json.loads((Path(base) / "meta.json").read_text())


def used_tool(base, ch):
    try:
        records = parse_log((Path(base) / "log").read_text())
    except FileNotFoundError:
        return False
    return any(status == 0 and ch.used_by(analyze(cmd)) for status, cmd in records)


def cmd_answer(base, value):
    meta = load_meta(base)
    ch = challenges.BY_ID[meta["challenge"]]
    if not ch.check(Path(base) / "arena", meta, value):
        if ch.kind == "trial":
            print(BAD + "✗ " + _("Not yet: the chest is still locked.") + f"{RESET} {DIM}(hint · task · flee){RESET}")
        elif ch.kind == "security":
            print(BAD + "✗ " + _("Not quite. Keep looking.") + f"{RESET} {DIM}(hint · task · flee){RESET}")
        else:
            print(BAD + "✗ " + _("Not quite. The {threat} shrugs it off.").format(threat=_(ch.threat))
                  + f"{RESET} {DIM}(hint · task · flee){RESET}")
        return 1
    if ch.kind == "fight" and not used_tool(base, ch):   # investigations: any way you like
        print(ACCENT + "✓ " + _("Right answer, but only `{tool}` can hurt the {threat}. "
                                "Solve it with {tool} (a successful command), then answer again.")
              .format(tool=ch.tool, threat=_(ch.threat)) + RESET)
        return 1
    return 0


def cmd_hint(base):
    meta = load_meta(base)
    ch = challenges.BY_ID[meta["challenge"]]
    i = min(meta.get("hints", 0), len(ch.hints) - 1)
    print(f"{ACCENT}💡 {ch.hint_text(i, meta)}{RESET}")
    meta["hints"] = i + 1
    (Path(base) / "meta.json").write_text(json.dumps(meta))
    return 0


def cmd_task(base):
    meta = load_meta(base)
    print(challenges.BY_ID[meta["challenge"]].task_text(meta))
    return 0


def banner(ch, task):
    return (f"\n{BAD}{BOLD}⚔ " + _("The {threat} attacks!").format(threat=_(ch.threat)) + f"{RESET}  "
            + _("Use {tool} to fight it.").format(tool=f"{BOLD}{ch.tool}{RESET}") + f"\n\n{task}\n\n"
            f"{DIM}" + _("You're in a sandbox folder with a real bash. Commands:") + f"{RESET}\n"
            "  answer <value>   " + _("strike") + f"   {DIM}("
            + _("needs a successful {tool} command first").format(tool=ch.tool) + f"){RESET}\n"
            "  hint             " + _("get a hint") + "\n"
            "  task             " + _("show the task again") + "\n"
            "  flee             " + _("run away (the threat will come back)") + "\n")


def arena(ch, intro, rng=None):
    """Run the sandbox bash for `ch`. `intro(task_text)` is printed first. Returns (won, notes)."""
    base = Path(tempfile.mkdtemp(prefix="bashou-arena-"))
    work = base / "arena"
    work.mkdir()
    meta = {"challenge": ch.id, "hints": 0}
    try:
        meta.update(ch.setup(work, rng or random.Random()))
        (base / "meta.json").write_text(json.dumps(meta))
        (base / "arena.rc").write_text(RC)
        print(intro(ch.task_text(meta)))
        env = {**os.environ, "BASHOU_ARENA": str(base),
               "BASHOU_SRC": str(Path(__file__).resolve().parent.parent)}
        code = subprocess.run(["bash", "--rcfile", str(base / "arena.rc"), "-i"], env=env).returncode
        try:
            records = parse_log((base / "log").read_text())
        except FileNotFoundError:
            records = []
    finally:
        if ch.cleanup:
            ch.cleanup(meta)
        shutil.rmtree(base, ignore_errors=True)

    notes = []
    now = datetime.datetime.now()
    with state.locked() as s:
        for status, cmd in records:                        # arena commands count too
            notes += progress.record(s, status, cmd, now.date().isoformat(), now.hour)
    return code == WIN, notes


def run():
    s = state.load()
    ch = pick(s)
    if not ch:
        print(DIM + _("No threat around. Your pet will warn you when one comes.") + RESET)
        return
    won, notes = arena(ch, lambda task: banner(ch, task))
    with state.locked() as s:
        if won:
            s["fights_won"] += 1
            if ch.id not in s["challenges"]:
                s["challenges"].append(ch.id)
            if s.get("threat") and s["threat"]["challenge"] == ch.id:
                s["threat"] = None
            notes += progress.unlock(s, ch.pet, _("beat the {threat}").format(threat=_(ch.threat)))
            notes += progress.check(s)
    if won:
        print(f"\n{GOOD}{BOLD}✨ " + _("You beat the {threat}!").format(threat=_(ch.threat)) + RESET)
    else:
        print(f"\n{DIM}" + _("You fled. The {threat} will be back.").format(threat=_(ch.threat)) + RESET)
    for note in notes:
        print(f"  {note}")
    print()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "answer":
        sys.exit(cmd_answer(sys.argv[3], sys.argv[2]))
    if cmd == "hint":
        sys.exit(cmd_hint(sys.argv[2]))
    if cmd == "task":
        sys.exit(cmd_task(sys.argv[2]))
    run()


if __name__ == "__main__":
    main()
