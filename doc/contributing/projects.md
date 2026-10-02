# Projects for `bashou project`

`bashou project` is for people who want to practise a language but don't know *what* to program. Each
project is a real, useful program (merge PDFs, sort photos by date, log internet outages…) built one
small step at a time: start very small, then add, improve and finish.

Bashou never reads the player's code. A step says **what** to do and **when it's done**, never how:
searching is part of learning. The player types `bashou project next` when the step is done; Bashou then
explains what that step taught (the why), and shows the next step, only that one. `bashou project hint`
gives one nudge, never the solution. Finished steps grow the Landscape pet.

No code needed: a project is one JSON file.

## Where

`bashou/project/en/<language>_<name>.json`. A translation is `bashou/project/<lang>/<same name>.json`
with only `title`, `pitch` and `steps` (the same number of steps, each with any of `do`, `done`, `hint`,
`why`); anything missing shows in English.

```json
{"id": "python_pdf", "order": 1, "language": "python", "name": "pdf", "difficulty": "very easy",
 "title": "Merge or split PDFs",
 "pitch": "Join scanned pages into one PDF, or take one page out of a long one…",
 "lessons": ["py_start", "py_flow"],
 "steps": [
  {"do": "Create a test folder and COPY two or three PDFs into it…",
   "done": "the folder holds 2 or 3 PDFs, and the originals are safe somewhere else.",
   "hint": "Any PDFs will do: an invoice, a ticket, a manual…",
   "why": "Working on copies is the first habit of anyone who writes programs that touch files…"}
 ]}
```

- **`language`**: `python`, `shell`, `c` or `rust`. Projects of a language you didn't tick in
  `bashou config skills` stay out of the list (unless you started one).
- **`name`**: what players type, `bashou project start python pdf`. Add it to `_bashou_projects` in
  `bashou.bash` for Tab (a test checks it). **`id`** is `<language>_<name>`.
- **`difficulty`**: `very easy`, `easy`, `medium` or `hard`. **`order`**: its place in the list.
- **`lessons`**: lessons (ids) that help. The list shows the first one the player hasn't read yet.
- **`steps`**: 5 or more. Each one ends with something that runs.

## How to write a step

Text players read to learn is written in **teacher style**: clear, complete sentences for beginners,
with the why and not only the what (see [questions.md](questions.md)).

- **`do`**: one small thing, said as an instruction. Not how: "create a folder for this year", not
  "call `os.makedirs`".
- **`done`**: something the player can check by themselves ("a 2026 folder appears"). It shows as
  "Done when: …", so start in lower case.
- **`hint`**: a direction, never the solution: a function or command to look up, a pitfall to think about.
- **`why`**: what this step taught, and why it matters in real programs. One or two sentences.
- **Safety first**: projects that touch files start on copies, show a dry run before acting, never
  overwrite silently, and move rather than delete.
- **Optional last steps** say "Optional:" at the start.

## Rewards

Every step counts for the Landscape's achievements (1, 3, 5, 10… 150 steps), and each project has its
own when it's finished, plus one per language and a few bonuses (`bashou/achievements.py`). A new
project needs its achievement there, in `PROJECT_ACHIEVEMENTS`; the tests check every project has one.
Finishing all the projects of any one language reaches the Landscape's last form, the Town.
