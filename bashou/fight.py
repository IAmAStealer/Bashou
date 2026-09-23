"""The arena: a bash sub-shell in a sandbox folder where you beat a threat with a real tool.

`bashou fight` runs `run()`. Inside the arena, the shell functions `answer`, `hint` and
`task` call back into this module (`python3 launch.py bashou.fight answer <base> <value>`).
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

from . import challenges, duel, progress, skills, state
from .analyze import analyze, parse_log
from .i18n import _, cap

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"
ACCENT, GOOD, BAD = "\033[38;2;150;190;230m", "\033[38;2;130;210;120m", "\033[38;2;240;110;110m"
WIN, FLEE, KO = 42, 3, 4   # exit codes of the arena shell (Ctrl-D is a flee, KO: no hearts left)
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
    if [[ -n $BASHOU_DUEL ]]; then
      python3 "$BASHOU_SRC/launch.py" bashou.duel judge "$BASHOU_ARENA"
      (( $? == 4 )) && exit 4
    fi
  fi
  _arena_hc=$HISTCMD
  _arena_tip
  return "$s"
}
_arena_tip() {
  local cmd
  cmd=$(HISTTIMEFORMAT= history 1)
  if [[ $cmd == *uniq* && $cmd != *sort*uniq* && -r $BASHOU_ARENA/tip_uniq ]]; then
    printf '%s\n' "$(< "$BASHOU_ARENA/tip_uniq")"
    rm -f "$BASHOU_ARENA/tip_uniq"
  fi
}
PROMPT_COMMAND=_arena_log
_arena() { python3 "$BASHOU_SRC/launch.py" bashou.fight "$@" "$BASHOU_ARENA"; }
answer() { _arena answer "$*" && exit 42; }
verify() { _arena verify && exit 42; }
hint() { _arena hint; }
task() { _arena task; }
flee() { exit 3; }
_arena_ps0() { [[ -r $BASHOU_ARENA/erase ]] && printf '%s' "$(< "$BASHOU_ARENA/erase")"; }
[[ -n $BASHOU_DUEL ]] && PS0='$(_arena_ps0)'
cd "$BASHOU_ARENA/arena"
"""


# --- threats ---------------------------------------------------------------

def level(s):
    return (len(s["pets"]) + sum(progress.stage(s, p) - 1 for p in s["pets"])
            + min(progress.starter_level(s), 9) - 1)            # the starter's first 9 levels


def remaining(s):
    return [c for c in challenges.ALL if c.id not in s["challenges"] and c.available()
            and skills.wanted(s, c.skill)]


def learned(s, tool):
    """You've met a tool: used it at least once, or had its lesson in `bashou adventure`."""
    lessons = (s.get("adventure") or {}).get("lessons", [])
    if tool == "|":
        return s["constructs"].get("pipe3", 0) > 0 or "pipes" in lessons
    return s["tools"].get(tool, 0) > 0 or tool in lessons


def ready(s, ch):
    """Beginners first: level 1 fights come anytime; harder ones once you've met their tool and
    beaten the fights they build on (the Knot Eel needed pipes and uniq nobody had shown you)."""
    if not all(a in s["challenges"] for a in ch.after):
        return False
    return ch.level == 1 or any(learned(s, t) for t in ch.tools)


def to_discover(s):
    """Tools of the next fights you can't get yet only because you haven't met them."""
    return list(dict.fromkeys(ch.tool for ch in remaining(s)       # once each: the pets pick one at random
                              if not ready(s, ch) and all(a in s["challenges"] for a in ch.after)))


def threats_per_day(s, today=None):
    """About 3 a day at first, 1 later, fewer when the bank runs low, none when it's empty
    (reviews that are due count as fights left)."""
    left = len(remaining(s)) + len(due(s, today))
    return max(1, min(3, 3 - level(s) // 3)) * min(1, left / 5)


# --- reviews: a beaten fight comes back after 1, 7 and 30 days (owner: learning is repetition) ---------

INTERVALS = (1, 7, 30)          # days before each review; after the last one the tool is acquired
REVIEW_FIRST = 0.6              # when reviews and new fights are both waiting, reviews usually go first


def due(s, today=None):
    """Beaten fights whose review day has come."""
    today = today or datetime.date.today().isoformat()
    return [challenges.BY_ID[cid] for cid, r in s.get("reviews", {}).items()
            if r["due"] <= today and cid in challenges.BY_ID and challenges.BY_ID[cid].available()]


def after_fight(s, ch, won, today=None):
    """Move `ch` along its reviews after a fight. Returns what to tell the player, or None."""
    today = datetime.date.fromisoformat(today) if today else datetime.date.today()
    reviews = s.setdefault("reviews", {})
    r = reviews.get(ch.id)
    if not won:
        if r and r["due"] <= today.isoformat():             # lost a review: start again tomorrow
            r.update(step=0, due=(today + datetime.timedelta(days=INTERVALS[0])).isoformat())
            return _("It'll be back tomorrow: the reviews start over.")
        return None
    if ch.id not in s["challenges"]:
        reviews[ch.id] = {"step": 0, "due": (today + datetime.timedelta(days=INTERVALS[0])).isoformat()}
        return _("It'll be back tomorrow: fighting it again is how `{tool}` sticks.").format(tool=ch.tool)
    if not r or r["due"] > today.isoformat():
        return None                                        # acquired already, or not due yet
    step = r["step"] + 1
    if step >= len(INTERVALS):
        del reviews[ch.id]
        return _("Last review won: `{tool}` is yours for good.").format(tool=ch.tool)
    r.update(step=step, due=(today + datetime.timedelta(days=INTERVALS[step])).isoformat())
    return _("Review {n}/{total} won. It'll be back in {days} days.").format(
        n=step, total=len(INTERVALS), days=INTERVALS[step])


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
    if s["threat_day"]["count"] >= threats_per_day(s, today) or now - s["last_threat"] < 2 * 3600:
        return None
    new, back = [ch for ch in remaining(s) if ready(s, ch)], due(s, today)
    if not (new or back) or rng.random() > 1 / 120:        # one chance in 120 per 30 s at the prompt
        return None
    review = bool(back) and (not new or rng.random() < REVIEW_FIRST)
    ch = rng.choice(back if review else new)
    s["threat"] = {"challenge": ch.id, "until": now + THREAT_MINUTES * 60, "review": review}
    s["threat_day"]["count"] += 1
    s["last_threat"] = now
    return announcement(s, now)


def announcement(s, now=None):
    """What the pet says about the waiting threat, or None."""
    t = active_threat(s, now)
    if not t or t["challenge"] not in challenges.BY_ID:
        return None
    ch = challenges.BY_ID[t["challenge"]]
    if t.get("review"):
        return "⚠ " + cap(_("The {threat} is back! Still remember `{tool}`? → bashou fight").format(
            threat=_(ch.threat), tool=ch.tool))
    return "⚠ " + cap(_("A {threat} is coming! Use `{tool}` to fight it → bashou fight").format(
        threat=_(ch.threat), tool=ch.tool))


def gone(challenge_id):
    """What the pet says when a threat got tired of waiting."""
    ch = challenges.BY_ID.get(challenge_id)
    name = _(ch.threat) if ch else "?"
    return "💨 " + cap(_("The {threat} got tired of waiting and left. It'll be back!").format(threat=name))


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
    return any(status == 0 and not (found := analyze(cmd)).help_only and ch.used_by(found)
               for status, cmd in records)


def cmd_answer(base, value):
    meta = load_meta(base)
    ch = challenges.BY_ID[meta["challenge"]]
    if ch.fix and value.strip() not in ("done", ""):
        print(ACCENT + "✗ " + _("Nothing to answer here: run `{value}` at the prompt, and when it works type `verify`.")
              .format(value=value.strip()) + RESET)
        return 1
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


def cmd_verify(base):
    """`verify`: the same strike as `answer`, named for fights where you do the job (fix a file…)."""
    ch = challenges.BY_ID[load_meta(base)["challenge"]]
    if not ch.fix:
        print(ACCENT + _("This one asks a question: answer <value>") + RESET)
        return 1
    return cmd_answer(base, "done")


def cmd_hint(base):
    meta = load_meta(base)
    ch = challenges.BY_ID[meta["challenge"]]
    i = min(meta.get("hints", 0), len(ch.hint_list(meta)) - 1)
    print(f"{ACCENT}💡 {ch.hint_text(i, meta)}{RESET}")
    meta["hints"] = i + 1
    (Path(base) / "meta.json").write_text(json.dumps(meta))
    return 0


def cmd_task(base):
    meta = load_meta(base)
    print(challenges.BY_ID[meta["challenge"]].task_text(meta))
    return 0


def banner(ch, task, review=None):
    """`review`: the fight's entry in s["reviews"] when it comes back for a review."""
    back = ""
    if review:
        back = f"{ACCENT}🔁 " + _("Review {n}/{total}: it came back on purpose. Beating it again after a break "
                                "is what makes `{tool}` stay with you.").format(
            n=review["step"] + 1, total=len(INTERVALS), tool=ch.tool) + f"{RESET}\n"
    return (f"\n{BAD}{BOLD}⚔ " + cap(_("The {threat} attacks!").format(threat=_(ch.threat))) + f"{RESET}  "
            + _("Use {tool} to fight it.").format(tool=f"{BOLD}{ch.tool}{RESET}") + f"\n{back}\n{task}\n\n"
            f"{DIM}" + _("You're in a sandbox folder with a real bash. Commands:") + f"{RESET}\n"
            + (strike_done(ch) if ch.fix else "  answer <value>   " + _("strike") + f"   {DIM}("
               + _("needs a successful {tool} command first").format(tool=ch.tool) + f"){RESET}\n")
            + "  hint             " + _("get a hint") + "\n"
            "  task             " + _("show the task again") + "\n"
            "  flee             " + _("run away (the threat will come back)") + "\n")


def strike_done(ch):
    """Fights where you fix a file: `answer` takes no value, Bashou checks the result itself."""
    return "  verify           " + _("strike when it works: Bashou checks your work") + "\n"


BEGINNER_WINS = 5          # until then, a fight's first hint teaches `tool --help` (owner)


def beginner(s):
    return s["fights_won"] < BEGINNER_WINS


def arena(ch, intro, rng=None, fight=False, help_first=False):
    """Run the sandbox bash for `ch`. `intro(task_text)` is printed first. Returns (exit code, notes).
    With `fight`, the duel is drawn at the top and wrong commands cost hearts (duel.py)."""
    base = Path(tempfile.mkdtemp(prefix="bashou-arena-"))
    work = base / "arena"
    work.mkdir()
    meta = {"challenge": ch.id, "hints": 0, "help_first": help_first}
    try:
        meta.update(ch.setup(work, rng or random.Random()))
        (base / "meta.json").write_text(json.dumps(meta))
        (base / "arena.rc").write_text(RC)
        (base / "tip_uniq").write_text(ACCENT + "💡 " + _(                # shown once, on uniq without sort
            "Tip: uniq only merges identical lines that are next to each other. "
            "Sort first: … | sort | uniq -c (or sort -u to keep one of each).") + RESET)
        top = duel.room(base) if fight else 0
        if top:                                            # the duel takes the top: start below it
            print("\033[H\033[2J" + "\n" * top, end="", flush=True)
        print(intro(ch.task_text(meta)), flush=True)
        env = {**os.environ, "BASHOU_ARENA": str(base),
               "BASHOU_SRC": str(Path(__file__).resolve().parent.parent)}
        env.pop("BASHOU_DUEL", None)
        if top:
            env["BASHOU_DUEL"] = "1"
        shell = subprocess.Popen(["bash", "--rcfile", str(base / "arena.rc"), "-i"], env=env)
        scene = duel.start(base, shell.pid) if top else None
        try:
            code = shell.wait()
        finally:
            duel.stop(scene)
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
    return code, notes


def run():
    s = state.load()
    ch = pick(s)
    if not ch:
        print(DIM + _("No threat around. Your pet will warn you when one comes.") + RESET)
        return
    review = s.get("reviews", {}).get(ch.id) if (s.get("threat") or {}).get("review") else None
    code, notes = arena(ch, lambda task: banner(ch, task, review), fight=True, help_first=beginner(s))
    won = code == WIN
    with state.locked() as s:
        told = after_fight(s, ch, won) if won or code == KO else None
        if not won:
            s["fights_lost"] = s.get("fights_lost", 0) + 1
            notes += progress.check(s)
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
    elif code == KO:
        print(f"\n{BAD}{BOLD}💫 " + _("Knocked out! The {threat} wins this time.").format(threat=_(ch.threat))
              + f"{RESET}\n{DIM}" + _("Only `{tool}` hurts it; looking around (ls, cat…) is free. "
                                       "It'll be back.").format(tool=ch.tool) + RESET)
    else:
        print(f"\n{DIM}" + _("You fled. The {threat} will be back.").format(threat=_(ch.threat)) + RESET)
    if told:
        print(f"{ACCENT}🔁 {told}{RESET}")
    for note in notes:
        print(f"  {note}")
    print()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "answer":
        sys.exit(cmd_answer(sys.argv[3], sys.argv[2]))
    if cmd == "verify":
        sys.exit(cmd_verify(sys.argv[2]))
    if cmd == "hint":
        sys.exit(cmd_hint(sys.argv[2]))
    if cmd == "task":
        sys.exit(cmd_task(sys.argv[2]))
    run()


if __name__ == "__main__":
    main()
