# Bashou

Claude is the owner of Bashou. Inside this repo, work autonomously: decide, implement, test and commit
without asking first. Only touch files in this repo; anything outside it still needs the user's OK.

- Local notes (untracked): `bug_report` (user's bug list), `.idea` (feature ideas), `doc/JOURNAL.md`,
  `doc/PLAN.md`. Read `doc/JOURNAL.md` to get back up to speed; add a line there after each change.
- When a fix or feature covers a line of `bug_report` or `.idea`, delete that line.
- Tests: `python3 -m unittest -q`. Every bug fix gets a regression test.
- After adding or changing bash that players see (lessons, questions, fights, projects): run the `bash-judge` agent.
- After adding or changing SQL that players see, or SQL in our Python: run the `sql-judge` agent.
- After adding or changing certificate content (lessons certs*, their questions, certs.py): run the `certs-judge` agent.
- Commit subjects are short sentences in plain English (they become release notes).
- Task-specific rules are mem guidelines (listed at session start with when to load them).
