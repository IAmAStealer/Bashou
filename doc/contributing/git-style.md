# git style: your own repository, a shared one

Bashou teaches git two ways, and every git sample belongs to one of them:

- **Your own repository** (nothing pushed yet): you can rewrite anything, `reset`, amend, rebase.
  The only risk is your own uncommitted work.
- **A shared repository** (pushed, others pulled): history is shared. Undo by adding commits
  (`revert`), never by rewriting what others have.

This file is the checklist for every git sample in Bashou: the `git` and `git_fix` lessons, the git
questions (in `bash.json`), the git fights of `bashou/challenges/gitfights.py`, their hints and
starter repositories. The `git-judge` agent (`.claude/agents/git-judge.md`) applies it after each
change, `tests/test_git_style.py` checks the text, and `tests/test_fight.py` plays every git fight.

Each rule has an id, used in reviews. A sample that breaks a rule on purpose (a wrong choice, the
mistake a fight shows) is marked ✘ and followed by the right form. The right answer, its explanation
and the hints must follow the rules.

Facts are checked by running git in a scratch repository, or against the git docs (git-scm.com) and
Pro Git, never from memory.

| Id | Rule | Why | Source |
|---|---|---|---|
| G1 | Branches with `git switch` (`-c` to create), files with `git restore` (`--staged` to unstage). `git checkout` is named only as the older form ("older git: `git checkout -b NAME`"). | `checkout` does both jobs, and `checkout -- file` silently throws away changes. switch and restore are in every git players run (2.23+). | [git-switch](https://git-scm.com/docs/git-switch), [git-restore](https://git-scm.com/docs/git-restore) |
| G2 | Every command that throws away uncommitted work says so where it's shown: `reset --hard`, `restore FILE`, `clean -f`, `checkout -- FILE`, `stash drop`. Teach `git stash` or a commit first. | Uncommitted changes aren't in any commit: git can't bring them back. | [git-reset](https://git-scm.com/docs/git-reset), [git-clean](https://git-scm.com/docs/git-clean) |
| G3 | Pushed commits are undone with `git revert`. `reset` and `commit --amend` only on commits that never left your machine. A force push is `--force-with-lease`, only on your own branch, and the text says why. | Rewriting shared history breaks everyone's next pull. | [git-revert](https://git-scm.com/docs/git-revert), [git-push --force-with-lease](https://git-scm.com/docs/git-push#Documentation/git-push.txt---force-with-lease), [Pro Git 7.6](https://git-scm.com/book/en/v2/Git-Tools-Rewriting-History) |
| G4 | The three places use Pro Git's words: working tree (your files), staging area or index (`git add`), commits (`HEAD`). `git status` and `git diff --staged` before a commit. | Every later doc uses these words. | [Pro Git 1.3](https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F) |
| G5 | `git add .` and `commit -a` are fine once `git status` was read. A sample that adds a secret, a build output or a huge file says to use `.gitignore`, and that `.gitignore` doesn't untrack a file already committed (`git rm --cached`). | The classic leaked `.env`. | [gitignore](https://git-scm.com/docs/gitignore), [git-rm](https://git-scm.com/docs/git-rm) |
| G6 | A secret that was pushed is changed (rotated), not just deleted: it stays in history and in every clone. | Deleting it in a new commit leaves it readable. | [GitHub: removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) |
| G7 | Conflicts are shown with git's real markers (`<<<<<<< HEAD`, `=======`, `>>>>>>> branch`), solved by editing, then `git add` and `git commit` (or `git rebase --continue`); `git merge --abort` to go back. | The markers are what the player will see in the file. | [git-merge: how conflicts are presented](https://git-scm.com/docs/git-merge#_how_conflicts_are_presented) |
| G8 | Never assume the first branch is `main` or `master`: say "main (or master)", or create it with `git init -b main`. | git's default depends on version and config (`init.defaultBranch`). | [git-init](https://git-scm.com/docs/git-init#Documentation/git-init.txt---initial-branchbranch-name) |
| G9 | `git pull` is said as fetch then merge (or rebase, with `pull.rebase`). Quoted git output is copied from a real run on the oldest git in the table, and its words must still be there in the newest. | git's hints and messages change between versions. | [git-pull](https://git-scm.com/docs/git-pull), [git release notes](https://github.com/git/git/tree/master/Documentation/RelNotes) |
| G10 | A commit message sample: a short subject line (about 50 characters, no final dot), a blank line, then the why. | `git log --oneline` and every tool show the first line. | [git-commit: discussion](https://git-scm.com/docs/git-commit#_discussion), [Pro Git 5.2](https://git-scm.com/book/en/v2/Distributed-Git-Contributing-to-a-Project#_commit_guidelines) |
| G11 | In a script, git is read through porcelain output made for programs (`git status --porcelain`, `git rev-parse`), not the human output. | Human output changes with version and language. | [git-status: porcelain](https://git-scm.com/docs/git-status#_porcelain_format_version_1) |

## Versions players run

| Where | git |
|---|---|
| Debian 12 | 2.39 |
| Debian 13 | 2.47 |
| Rocky 9 | 2.43 (9.4) to 2.52 (current), updated in minor releases |
| macOS (Xcode command line tools) | Apple Git, 2.39 or newer |
