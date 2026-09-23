# Bashou

Claude is the owner of Bashou. Inside this repo, work autonomously: decide, implement, test and commit
without asking first. Only touch files in this repo; anything outside it still needs the user's OK.

- Local notes (untracked): `bug_report` (user's bug list), `.idea` (feature ideas), `doc/JOURNAL.md`,
  `doc/PLAN.md`. Read `doc/JOURNAL.md` to get back up to speed; add a line there after each change.
- When a fix or feature covers a line of `bug_report` or `.idea`, delete that line.
- Tests: `python3 -m unittest -q`. Every bug fix gets a regression test.
- Commit subjects are short sentences in plain English (they become release notes).
- Text players read to learn (adventure questions and explanations, fight tasks, hints, `bashou learn`,
  `bashou explain`) is written in **teacher style**: clear, complete sentences for beginners, the why
  and not only the what. The global "concise" rule doesn't apply there. See doc/contributing/questions.md.
