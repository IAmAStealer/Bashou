# Lessons for `bashou lesson`

`bashou lesson` opens the Sage Owl's library: lessons you read page by page. A hint says what to
type; a lesson shows **how things work**, with a small drawing (a scheme) that grows from page to
page and the owl pointing its wing at the line that matters.

Lessons unlock with what you do (fights, achievements, commands), never by reading another lesson.
Each one prepares the **next** step, not the one you are on: the stack and the heap unlock after your
first C fight, before the fights about leaks and runaway recursion. Locked lessons show in the list
with what unlocks them, so players see the road ahead.

In the list, an open lesson is **green** while it's your next step, and turns back to white once
you've **mastered** it: its `masters` conditions hold (the fights and achievements it prepares for).

No code needed: a lesson is one JSON file.

## Where

`bashou/lesson/en/<id>.json`. A translation is `bashou/lesson/<lang>/<id>.json` with only `title`,
`summary` and `pages` (the same number of pages); anything missing shows in English.

```json
{"id": "stack_heap", "order": 110, "skill": "c",
 "needs": ["won semicolon_slug | tool gcc 3"],
 "masters": ["won leak_lurker", "won stack_specter"],
 "title": "C memory: the stack and the heap",
 "summary": "Where your variables live, why malloc needs free, and what a leak is.",
 "pages": [
  {"scheme": [" stack                     heap",
              " ┌──────────────┐          ┌─────────────┐",
              " │ main   p ────┼─────────▶│ 100 bytes   │",
              " └──────────────┘          └─────────────┘"],
   "point": 2, "mark": ["malloc", "100 bytes"],
   "text": ["malloc asks for memory on the heap and gives you its address.", "",
            "- p is a pointer: a small variable, on the stack, that holds that address.",
            "$ gcc -g -fsanitize=address prog.c -o prog"]}
 ]}
```

- `order`: place in the list. `skill`: one of `bashou skills`, or a list of them (the lesson only
  shows to players who learn one); leave it out for lessons everyone gets.
- `needs`: what unlocks it. All of them must hold; `a | b` holds when one side does. Conditions:
  `commands N`, `tool NAME N` (used N times), `won FIGHT_ID`, `fights N` (won), `achievement ID`.
  The list shows the missing ones in words, with progress ("run 50 commands (32/50)").
- `masters`: same conditions, what shows the player knows it now (usually the fights it prepares).
- `fights`: the fights this lesson helps with. **Every fight needs at least one lesson** (a test checks
  it): meeting one of these fights opens the lesson even when `needs` don't hold yet, and `lesson` in
  the arena opens it. Place the lesson in its track in [curriculum.md](curriculum.md).
- `scheme` (optional): lines of text, **50 columns at most**, 14 lines at most. `point`: the line
  (from 0) the owl points at. `mark`: words shown in color, usually what changed since the page
  before.
- `text`: one entry per line. `""` is a blank line, `- ` starts a bullet, `$ ` a command (green).

## Style

- **One idea per page.** A scheme plus 3 to 5 short lines. Several short pages beat one dense page.
- **Let the drawing grow.** Keep the same drawing from page to page and change one thing: the
  reader follows the change (the owl points at it, `mark` colors it).
- **Air.** Lists and examples, blank lines between groups; never a block of five dense lines.
- **Teacher style** (see [questions.md](questions.md)): complete sentences for beginners, the why and
  not only the what, no unexplained jargon.
- **Draw only when it helps**: structures, flows, before/after, where things are. A list in boxes
  is still a list.
- **True today**: check facts against primary docs (man pages, official documentation).

## Check

```bash
python3 tools/lesson_preview.py stack_heap     # every page, as an 80×24 terminal shows it
python3 -m unittest tests.test_lesson          # widths, heights, points, conditions, translations
```

With Claude Code, the `scheme-judge` agent (`.claude/agents/scheme-judge.md`) reviews a new lesson:
is each drawing needed, true (checked on the web), and readable.
