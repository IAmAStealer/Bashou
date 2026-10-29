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
- After adding or changing Python that players see (py_* lessons, questions, Python fights, python_* projects): run the `python-judge` agent.
- After adding or changing Rust that players see (rust_* lessons, rust questions, Rust fights): run the `rust-judge` agent.
- After adding or changing C that players see (compilation, gcc_use, stack_heap, pointers, debugger, c questions, C fights): run the `c-judge` agent.
- After adding or changing git that players see (the git lesson, git questions, git fights): run the `git-judge` agent.
- After adding or changing network content (network, ip_addr, ipv6, dns*, tcp, net_debug, network questions and fights; not certificates): run the `network-judge` agent.
- After adding or changing package content (packages, repos, debian and rocky questions and fights): run the `packages-judge` agent.
- After adding or changing CI/CD content (pipeline, cicd questions and fights): run the `cicd-judge` agent.
- After adding or changing logic content (logic lesson, logic questions and fights, conditions shown elsewhere): run the `logic-judge` agent.
- After adding or changing AI content (ai_* lessons, ai questions): run the `ai-judge` agent.
- After adding or changing Linux system content (users, permissions, processes, disk, archives, services, pass lessons; linux and systemd questions; system, security and secrets fights): run the `linux-judge` agent.
- Commit subjects are short sentences in plain English (they become release notes).
- Task-specific rules are mem guidelines (listed at session start with when to load them).
