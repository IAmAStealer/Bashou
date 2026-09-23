"""`bashou adventure`: your starter walks into the world, seen from behind.

Screens (phases): intro → fork → walk → monster / chest / lesson → … → boss → fork → … → chapter end.
The rules live in world.py; this file draws and reads keys.
"""

import os
import random
import select
import sys
import termios
import time
import tty
from pathlib import Path

from .. import challenges, fight, progress, render, skills, state
from ..i18n import _, cap
from . import canvas, lessons, quiz, scene, sprites, world

ESC = "\x1b"
FPS = 15
SPEED = 5.0                    # world units per second: the pet walks on its own between events
BOSS_SECONDS = 20
QUIT_KEYS = ("s", "S", "q", "Q", ESC, "\x03", "\x04")
UP, DOWN, LEFT, RIGHT = "\x1b[A", "\x1b[B", "\x1b[D", "\x1b[C"
ENTER = ("\r", "\n")
PANEL_BG, PANEL_FG, ACCENT, GOOD, BAD = (28, 28, 40), (235, 235, 240), (150, 190, 230), (130, 210, 130), (240, 110, 110)


def load():
    adv = state.load().get("adventure") or {}
    if "chapter" not in adv:                       # a walk from the first preview: keep the meters
        adv = {**world.new(), "walked": adv.get("distance", 0.0)}
    if adv.get("phase") == "rest":                 # campfires are gone
        world.event_done(adv)
    return {**world.new(), **adv}


def save(adv):
    """Save, and return the achievements and pets it earned (🏆 / 🎉 lines)."""
    with state.locked() as s:
        s["adventure"] = adv
        return progress.check(s)


def biome_name(biome):
    return {"meadow": _("Meadow"), "hills": _("Hills"), "forest": _("Forest"), "sand": _("Desert"),
            "water": _("Lake"), "dungeon": _("Dungeon")}[biome]


def topic_name(topic):
    return world.TOPICS[topic][0]



def solution(q):
    """What the player reads after answering: the right choice, then why (a few sentences)."""
    return [f"✔ {q['choices'][q['answer']]}", q["explain"]]

class Game:
    def __init__(self, cols, rows, rng=random):
        self.adv = load()
        self.rng = rng
        s = state.load()
        self.topics = skills.picked(s)
        self.frames, self.palette = sprites.hero(progress.current(s, "starter")[0])
        self.quit = False
        self.choice = 0                 # highlighted fork path or answer
        self.question = None            # the question on screen
        self.result = None              # (good?, lines) after an answer
        self.signs = []                 # the paths' names written on the road at a fork
        self.boss = None                # {"left": questions left, "total", "deadline"}
        self.panel_rect = None
        self.captioned = False          # the top line holds a caption (repaint the sky when it goes)
        self.trial = None               # the chest's shell trial
        self.pending_trial = None       # set when you open it: main() runs the sandbox shell
        self.page = 0                   # lesson page
        if self.adv["phase"] in ("monster", "boss", "chest", "lesson"):
            self.start_event(self.adv["phase"], time.time())   # an event you quit in: start it again
        self.resize(cols, rows)

    def resize(self, cols, rows):
        self.cols, self.rows = cols, rows
        self.canvas = canvas.Canvas(cols, (rows - 1) * 2)
        self.scale = 2 if self.canvas.h >= 40 else 1

    # --- rules ---------------------------------------------------------------------------------

    def start_event(self, kind, now):
        adv = self.adv
        self.choice, self.result = 0, None
        if kind == "monster":
            self.question = self.ask()
        elif kind == "boss":
            total = world.boss_questions(adv)
            self.boss = {"left": total, "total": total}
            self.question = self.ask(boss=True, now=now)
        elif kind == "chest":
            self.trial = self.pick_trial()
        elif kind == "lesson":
            self.page = 0

    def pick_trial(self):
        """A shell trial for this chapter's level, one you haven't opened yet if possible."""
        adv = self.adv
        taught = lessons.BY_ID.get(adv.get("path_lesson") or "")
        if taught and taught["id"] in adv["lessons"]:        # just learned: practice it now
            pool = [t for t in challenges.TRIALS if taught["tool"] in t.tools and t.available()]
            fresh = [t for t in pool if t.id not in adv["trials"]]
            if pool:
                return self.rng.choice(fresh or pool)
        lvl = min(3, adv["chapter"])
        pool = [t for t in challenges.TRIALS if t.level == lvl and not t.tools and t.available()]
        fresh = [t for t in pool if t.id not in adv["trials"]]
        return self.rng.choice(fresh or pool)

    def trial_seed(self):
        return f"{self.trial.id}:{self.adv['walked']:.1f}"

    def trial_meta(self):
        """Placeholders of the chest's task, so the box shows the same names as the shell will."""
        if getattr(self, "_meta_for", None) != self.trial.id:
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                self._meta = self.trial.setup(Path(tmp), random.Random(self.trial_seed()))
            self._meta_for = self.trial.id
        return self._meta

    def trial_done(self, won, notes):
        adv = self.adv
        if won:
            if self.trial.id not in adv["trials"]:
                adv["trials"].append(self.trial.id)
            healed = adv["hearts"] < world.HEARTS
            adv["hearts"] = min(world.HEARTS, adv["hearts"] + 1)
            self.result = (True, [_("The chest opens! Inside: a heart. ♥ +1") if healed else
                                  _("The chest opens! Inside: a shiny pebble. Your pet looks very proud.")] + notes)
        else:
            self.result = (False, [_("The chest stays shut. Maybe next time.")] + notes)
        self.result = (self.result[0], self.result[1] + save(adv))

    def ask(self, boss=False, now=0.0):
        adv = self.adv
        q = quiz.pick(adv["topic"], world.level(adv, adv["topic"]), adv["seen"], self.rng)
        adv["seen"] = (adv["seen"] + [q["id"]])[-400:]
        if boss:
            self.boss["deadline"] = now + BOSS_SECONDS
        return q

    def answer(self, i, now):
        adv, q = self.adv, self.question
        right = i == q["answer"]
        if right:
            adv["correct"] = adv.get("correct", 0) + 1         # 20 bring the Frog
        explain = solution(q)
        if adv["phase"] == "monster":
            if right:
                self.result = (True, [_("Right! The monster runs away.")] + explain)
            elif world.lose_heart(adv):
                self.result = (False, [_("Wrong… and that was your last heart.")] + explain
                               + [_("Back to the last checkpoint: you can pick another path.")])
            else:
                self.result = (False, [_("Wrong! ♥ -1")] + explain)
        else:
            self.boss_answer(right, explain, now)
        self.question = None

    def boss_answer(self, right, explain, now):
        adv = self.adv
        topic = adv["topic"]
        if not right:
            name = _(world.TOPICS[topic][2])
            if not world.lose_heart(adv):
                self.result = (False, [cap(_("The {boss} hits you! ♥ -1").format(boss=name))] + explain)
                return
            self.boss = None
            self.result = (False, [cap(_("The {boss} wins this time.").format(boss=name))] + explain
                           + [_("Back to the last checkpoint. Bosses are there to make it stick!")])
            save(adv)
            return
        self.boss["left"] -= 1
        if self.boss["left"] > 0:
            self.result = (True, [_("Hit! {n} to go.").format(n=self.boss["left"])] + explain)
            return
        name = _(world.TOPICS[topic][2])
        world.boss_won(adv)
        self.boss = None
        self.result = (True, [_("Victory! The {boss} is defeated.").format(boss=name),
                              _("Checkpoint saved. {topic} is now level {level}.").format(
                                  topic=topic_name(topic), level=world.level(adv, topic))] + save(adv))

    def close_result(self, now):
        adv = self.adv
        self.result = None
        if adv["phase"] in ("monster", "chest", "lesson"):
            world.event_done(adv)
        elif adv["phase"] == "boss" and self.boss:            # next boss question
            self.question = self.ask(boss=True, now=now)

    # --- input -----------------------------------------------------------------------------------

    def key(self, k, now):
        adv = self.adv
        if k in QUIT_KEYS:
            self.quit = True
            return
        if self.result:
            if k in ENTER or k == " ":
                self.close_result(now)
            return
        phase = adv["phase"]
        if phase == "intro" and (k in ENTER or k == " "):
            adv["phase"] = "fork"
        elif phase == "fork":
            options = world.fork_options(adv, self.topics)
            if k in (LEFT, UP, "h"):
                self.choice = (self.choice - 1) % len(options)
            elif k in (RIGHT, DOWN, "l"):
                self.choice = (self.choice + 1) % len(options)
            elif k.isdigit() and 1 <= int(k) <= len(options):
                self.choice = int(k) - 1
            elif k in ENTER:
                world.choose(adv, options[self.choice])
                self.choice = 0
                save(adv)
        elif phase in ("monster", "boss") and self.question:
            n = len(self.question["choices"])
            if k in (UP, "k"):
                self.choice = (self.choice - 1) % n
            elif k in (DOWN, "j"):
                self.choice = (self.choice + 1) % n
            elif k.lower() in "abcd" and k:
                self.answer("abcd".index(k.lower()), now)
            elif k in "1234" and k:
                self.answer(int(k) - 1, now)
            elif k in ENTER:
                self.answer(self.choice, now)
        elif phase == "lesson" and (k in ENTER or k == " "):
            lesson = lessons.BY_ID[adv["path_lesson"]]
            self.page += 1
            if self.page >= len(lesson["pages"]):
                if lesson["id"] not in adv["lessons"]:
                    adv["lessons"].append(lesson["id"])
                self.result = (True, [_("The owl nods: now try it, the next chest uses it.")] + save(adv))
        elif phase == "chest" and not self.result:
            if k in ENTER:
                self.pending_trial = self.trial
            elif k == " ":
                self.result = (False, [_("You leave the chest behind.")])
        elif phase == "chapter_end" and k in ENTER:
            world.next_chapter(self.adv)
            save(self.adv)

    def walking(self, now):
        return self.adv["phase"] == "walk"

    def update(self, dt, now):
        adv = self.adv
        if self.walking(now):
            event = world.walk(adv, SPEED * dt)
            if event:
                self.start_event(event, now)
        if adv["phase"] == "boss" and self.question and now > self.boss["deadline"]:
            q = self.question
            self.question = None
            self.boss_answer(False, [_("Too slow!")] + solution(q), now)

    # --- drawing ---------------------------------------------------------------------------------

    def draw(self, t, now):
        adv, c = self.adv, self.canvas
        signs = self.draw_fork(t)
        lines = self.panel(now)
        rect = self.panel_box(lines)
        step = int(adv["walked"] * 1.5) % len(self.frames) if self.walking(now) else 0
        w, h = 17 * self.scale, 12 * self.scale
        c.sprite(self.frames[step], self.palette, (c.w - w) // 2, c.h - h - 1, self.scale)
        self.draw_ahead(t, (rect[0] - 1) * 2 if rect else None)
        if rect != self.panel_rect and self.panel_rect:
            self.forget(self.panel_rect)                     # repaint what the old panel covered
        self.panel_rect = rect
        caption = self.caption()
        if self.captioned and not caption:
            for col in range(c.w):
                c.shown.pop((0, col), None)
        self.captioned = bool(caption)
        return c.render() + self.panel_text(lines, rect) + caption + self.fork_signs(signs)

    def draw_fork(self, t):
        """Paint the scene. At the start and at a fork the road splits into the paths you can take
        (a Y, or three); returns their names and where they go on screen (line, column, text, picked)."""
        adv = self.adv
        fork = None
        if adv["phase"] in ("intro", "fork") and not self.result:
            options = world.fork_options(adv, self.topics)
            picked = self.choice if adv["phase"] == "fork" else None
            fork = (len(options), picked, 12 * self.scale)
        spots = scene.draw(self.canvas, world.biome(adv), adv["distance"], t, 17 * self.scale, fork)
        if not fork or fork[1] is None:
            return []
        signs = []
        for i, (topic, (x, y)) in enumerate(zip(options, spots)):
            name = f"{topic_name(topic)} · " + _("level {n}").format(n=world.level(adv, topic))
            text = f"▶ {name} ◀" if i == picked else f" {name} "
            col = int(x) - render.width(text) // 2 + 1
            col = max(1, min(col, self.cols - render.width(text)))
            signs.append((max(2, int(y) // 2 + 1), col, text, i == picked))
        return signs

    def fork_signs(self, signs):
        """Write the paths' names on the road; the canvas repaints where old names were."""
        for line, col, text, _picked in self.signs:
            if (line, col, text, _picked) not in signs:
                for k in range(render.width(text)):
                    self.canvas.shown.pop((line - 1, col - 1 + k), None)
        self.signs = signs
        out = []
        for line, col, text, picked in signs:
            color = ACCENT if picked else PANEL_FG
            out.append(f"{ESC}[{line};{col}H{ESC}[0m{ESC}[48;2;%d;%d;%dm" % PANEL_BG
                       + (f"{ESC}[1m" if picked else "") + f"{ESC}[38;2;%d;%d;%dm" % color + text + f"{ESC}[0m")
        return "".join(out)

    def caption(self):
        """At the start no box hides the road: one line on top names the chapter, the keys are on
        the bottom line. At a fork the paths' names are written on the road (draw_fork)."""
        adv = self.adv
        if adv["phase"] == "intro":
            ch = world.chapter(adv["chapter"])
            parts = [(_("Chapter {n}: {title}").format(n=adv["chapter"], title=world.title(ch)), ACCENT, True)]
        else:
            return ""
        width = sum(render.width(text) for text, _c, _b in parts)
        pad = max(0, (self.cols - width) // 2)
        out = [f"{ESC}[1;1H{ESC}[0m{ESC}[48;2;%d;%d;%dm{ESC}[2K" % PANEL_BG, " " * pad]
        for text, color, bold in parts:
            out.append((f"{ESC}[1m" if bold else f"{ESC}[22m") + f"{ESC}[38;2;%d;%d;%dm" % color + text)
        out.append(" " * max(0, self.cols - pad - width))
        return "".join(out) + f"{ESC}[0m"

    def draw_ahead(self, t, room=None):
        """What waits on the road: the next event growing as you come closer, or the signpost.
        With a box on screen (`room` = pixel rows free above it), it stands in the space left."""
        adv = self.adv
        phase = adv["phase"]
        if phase in ("fork", "intro"):
            return                                            # the road itself splits: draw_fork()
        if phase == "walk":
            kind = world.events(adv)[adv["segment"]]
            rel = world.next_event_at(adv) - adv["distance"] + 3
        elif phase in ("monster", "boss", "chest", "lesson"):
            kind, rel = phase, 3.0 if phase != "boss" else 2.2
        else:
            return
        if rel > scene.FAR:
            return
        rows, palette = sprites.ahead(kind, adv["topic"])
        bob = 1 if kind in ("monster", "boss") and int(t * 3) % 2 else 0
        if room:
            share = {"boss": 0.9, "monster": 0.6}.get(kind, 0.4)
            scale = max(1.0, min(room * share / len(rows), self.canvas.w * 0.5 / len(rows[0])))
            scene.blit(self.canvas, rows, palette, self.canvas.w / 2, room - 1 - bob, scale)
            return
        horizon = int(self.canvas.h * 0.38)
        y = horizon + scene.CAMERA / rel
        near = (y - horizon) / (self.canvas.h - horizon)
        scale = near * (3.0 if kind == "boss" else 2.0) * self.scale
        scene.blit(self.canvas, rows, palette, self.canvas.w / 2, min(y, self.canvas.h - 12 * self.scale - 2) - bob, scale)

    def panel(self, now):
        """Lines of the box over the sky: (text, color) pairs."""
        adv = self.adv
        phase = adv["phase"]
        if self.result:
            good, texts = self.result
            return ([(texts[0], GOOD if good else BAD)] + [(t, PANEL_FG) for t in texts[1:]]
                    + [("", PANEL_FG), (_("Enter: continue"), ACCENT)])
        if phase in ("intro", "fork"):
            return []                                         # the road stays in view: see caption()
        if phase in ("monster", "boss") and self.question:
            q = self.question
            if phase == "boss":
                left = max(0.0, self.boss["deadline"] - now)
                bar = "█" * int(left) + "░" * (BOSS_SECONDS - int(left))
                head = [(_("{boss} · {n}/{total}").format(boss=cap(_(world.TOPICS[adv["topic"]][2])),
                                                           n=self.boss["total"] - self.boss["left"] + 1,
                                                           total=self.boss["total"]), BAD),
                        (f"⏳ {bar} {int(left)}s", BAD if left < 6 else ACCENT)]
            else:
                head = [(_("A wild {topic} monster asks:").format(topic=topic_name(adv["topic"])), ACCENT)]
            out = head + [(q["q"], PANEL_FG), ("", PANEL_FG)]
            for i, choice in enumerate(q["choices"]):
                mark = "▶ " if i == self.choice else "  "
                out.append((f"{mark}{'ABCD'[i]}. {choice}", ACCENT if i == self.choice else PANEL_FG))
            return out
        if phase == "lesson":
            lesson = lessons.BY_ID[adv["path_lesson"]]
            text, example = lesson["pages"][min(self.page, len(lesson["pages"]) - 1)]
            return [(_("🦉 The Sage Owl teaches: {title} ({n}/{total})").format(
                        title=_(lesson["title"]), n=self.page + 1, total=len(lesson["pages"])), ACCENT),
                    (_(text), PANEL_FG), ("", PANEL_FG), (f"  $ {example}", GOOD), ("", PANEL_FG),
                    (_("Enter: next"), ACCENT)]
        if phase == "chest" and self.trial:
            return [(_("A locked chest! It opens with a shell trick:"), ACCENT),
                    (self.trial.task_text(self.trial_meta()), PANEL_FG), ("", PANEL_FG),
                    (_("Enter: open it (a real shell opens) · space: leave it"), ACCENT)]
        if phase == "chapter_end":
            nxt = world.chapter(adv["chapter"] + 1)
            return [(_("Chapter {n} complete!").format(n=adv["chapter"]), GOOD),
                    (_("A new quest calls you, hero: {title}.").format(title=world.title(nxt)), PANEL_FG),
                    ("", PANEL_FG), (_("Enter: accept · s: save & quit"), ACCENT)]
        return []

    def panel_box(self, lines):
        if not lines:
            return None
        width = min(self.cols - 4, 76)
        wrapped = [(part, color) for text, color in lines
                   for part in (render.wrap(text, width - 4, 8) if text else [""])]
        top = max(1, self.rows - 2 - len(wrapped))          # just above the status line
        return (top, (self.cols - width) // 2 + 1, width, wrapped)

    def panel_text(self, lines, rect):
        if not rect:
            return ""
        top, left, width, wrapped = rect
        bg = "48;2;%d;%d;%d" % PANEL_BG
        out = [f"{ESC}[{top};{left}H{ESC}[{bg};38;2;%d;%d;%dm╭{'─' * (width - 2)}╮" % ACCENT]
        for i, (text, color) in enumerate(wrapped):
            pad = width - 4 - render.width(text)
            out.append(f"{ESC}[{top + 1 + i};{left}H{ESC}[{bg};38;2;%d;%d;%dm│ " % ACCENT
                       + f"{ESC}[38;2;%d;%d;%dm" % color + text + " " * pad
                       + f"{ESC}[38;2;%d;%d;%dm │" % ACCENT)
        out.append(f"{ESC}[{top + 1 + len(wrapped)};{left}H{ESC}[{bg};38;2;%d;%d;%dm╰{'─' * (width - 2)}╯" % ACCENT)
        return "".join(out) + f"{ESC}[0m"

    def forget(self, rect):
        top, left, width, wrapped = rect
        for line in range(top - 1, top + len(wrapped) + 1):
            for col in range(left - 1, left - 1 + width):
                self.canvas.shown.pop((line, col), None)

    def hud(self):
        adv = self.adv
        hearts = "♥" * adv["hearts"] + "♡" * (world.HEARTS - adv["hearts"])
        where = biome_name(world.biome(adv))
        path = f" · {topic_name(adv['topic'])} " + _("level {n}").format(n=world.level(adv, adv["topic"])) \
            if adv["topic"] else ""
        keys = {"intro": _("Enter: set off · s: save & quit"),
                "fork": _("←/→ choose · Enter: go · s: save & quit")}.get(adv["phase"], _("s: save & quit"))
        if self.result:
            keys = _("s: save & quit")
        info = f"{_('Chapter {n}').format(n=adv['chapter'])} · {where}{path} · {hearts} · {int(adv['walked'])} m"
        text = f" {keys}   {info}" if adv["phase"] in ("intro", "fork") and not self.result else f" {info}   {keys}"
        return f"{ESC}[{self.rows};1H{ESC}[0m{ESC}[2K{text[:self.cols - 1]}"


def main():
    if not sys.stdin.isatty():
        print(_("The adventure needs a terminal."))
        return 1
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    size = os.get_terminal_size()
    if size.columns < 50 or size.lines < 20:
        print(_("Make the terminal a bit bigger for the adventure (50×20 at least)."))
        return 1
    game = Game(size.columns, size.lines)
    out = sys.stdout
    out.write(f"{ESC}[?1049h{ESC}[?25l{ESC}[2J")
    start = last = time.time()
    try:
        tty.setcbreak(fd)
        while not game.quit:
            now = time.time()
            size = os.get_terminal_size()
            if (size.columns, size.lines) != (game.cols, game.rows):
                game.resize(size.columns, size.lines)
                out.write(f"{ESC}[2J")
            game.update(now - last, now)
            last = now
            if game.pending_trial:
                run_trial(game, fd, old, out)
                continue
            out.write(game.draw(now - start, now) + game.hud())
            out.flush()
            if select.select([fd], [], [], 1 / FPS)[0]:
                data = os.read(fd, 32).decode(errors="ignore")
                for k in split_keys(data):
                    game.key(k, time.time())
    except KeyboardInterrupt:
        pass
    finally:
        notes = save(game.adv)
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        out.write(f"{ESC}[0m{ESC}[?25h{ESC}[?1049l")
        out.flush()
    print("  " + _("Adventure saved: chapter {n}, {m} m walked. Come back with: bashou adventure").format(
        n=game.adv["chapter"], m=int(game.adv["walked"])))
    for note in notes:
        print(f"  {note}")
    return 0


def run_trial(game, fd, old, out):
    """Leave the game screen for a real sandbox shell, then come back where we were."""
    trial, game.pending_trial = game.pending_trial, None
    termios.tcsetattr(fd, termios.TCSADRAIN, old)
    out.write(f"{ESC}[0m{ESC}[?25h{ESC}[?1049l")
    out.flush()
    code, notes = fight.arena(trial, lambda task: trial_intro(task), random.Random(game.trial_seed()))
    won = code == fight.WIN
    tty.setcbreak(fd)
    out.write(f"{ESC}[?1049h{ESC}[?25l{ESC}[2J")
    game.canvas.shown = {}                     # the whole screen is drawn again
    game.trial_done(won, notes)


def trial_intro(task):
    b, d, r = "\033[1m", "\033[2m", "\033[0m"
    return (f"\n{b}🧰 " + _("A locked chest!") + f"{r}\n\n{task}\n\n"
            f"{d}" + _("A real shell, in a sandbox folder. Commands:") + f"{r}\n"
            "  answer           " + _("check (answer <value> when there's a question)") + "\n"
            "  hint             " + _("get a hint") + "\n"
            "  task             " + _("show the task again") + "\n"
            "  flee             " + _("leave the chest and go back to the adventure") + "\n")


def split_keys(data):
    """Split a read into keys: arrow escapes stay whole."""
    keys, i = [], 0
    while i < len(data):
        if data[i] == ESC and data[i + 1:i + 2] == "[" and i + 2 < len(data):
            keys.append(data[i:i + 3])
            i += 3
        else:
            keys.append(data[i])
            i += 1
    return keys
