"""Git fights, in a small repository made for each fight: commit only what belongs together, work on a
branch, settle a merge conflict."""

import subprocess

from . import Challenge
from .trials import trial

IDEAS = ("dark mode", "a search box", "bigger buttons", "a help page", "keyboard shortcuts", "an undo button")


def git(work, *args):
    """git in the repository; its output, or None when it fails."""
    try:
        done = subprocess.run(["git", *args], cwd=work, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def repo(work):
    """A fresh repository with its own name and email (none is needed from the player). No auto gc or
    maintenance: since git 2.47 it runs detached after a commit and wrote into .git while it was deleted."""
    git(work, "init", "-q", "-b", "main")
    if git(work, "rev-parse", "--git-dir") is None:            # git before 2.28: no -b
        git(work, "init", "-q")
        git(work, "symbolic-ref", "HEAD", "refs/heads/main")
    for key, value in (("user.name", "Bashou"), ("user.email", "bashou@example.invalid"),
                       ("commit.gpgsign", "false"), ("core.editor", "true"), ("merge.conflictstyle", "merge"),
                       ("gc.auto", "0"), ("maintenance.auto", "false")):
        git(work, "config", key, value)


def commit(work, message, *files):
    git(work, "add", *files)
    git(work, "commit", "-q", "-m", message)


# --- Commit Crowd: stage one file, not the whole crowd ------------------------------------------------

def crowd_setup(work, rng):
    repo(work)
    (work / "notes.txt").write_text("Shopping: bread\n")
    (work / "todo.txt").write_text("Call the plumber\n")
    commit(work, "First notes", "notes.txt", "todo.txt")
    (work / "notes.txt").write_text("Shopping: bread\nShopping: milk\n")
    (work / "todo.txt").write_text("Call the plumber\nHalf-written line, not ready\n")
    (work / "draft.txt").write_text("an unfinished draft\n")
    return {}


def crowd_verify(work, meta, value):
    """One new commit with notes.txt alone; todo.txt still changed, draft.txt still untracked."""
    count = git(work, "rev-list", "--count", "HEAD")
    changed = git(work, "diff", "--name-only", "HEAD~1", "HEAD")
    status = git(work, "status", "--porcelain")
    return (count is not None and count.strip() == "2" and changed is not None and changed.split() == ["notes.txt"]
            and status is not None and sorted(status.splitlines()) == [" M todo.txt", "?? draft.txt"])


COMMIT_CROWD = Challenge(
    level=1, id="commit_crowd", pet="beaver", tools=("git",), threat="Commit Crowd", requires=["git"], fix=True,
    task="The Commit Crowd wants to sneak into your next commit: notes.txt, todo.txt and draft.txt all "
         "changed.\nCommit only notes.txt (any message). todo.txt isn't ready and draft.txt stays out. "
         "Then: verify",
    help="Here, look at git add --help and git commit --help: what goes into a commit is what you add.",
    hints=["A commit takes what is staged (added), not every change. git status shows three groups: staged, "
           "changed but not staged, untracked. git add picks the files one by one. Avoid git add . or "
           "git commit -a here: they take the whole crowd.",
           "Try: git add notes.txt, then git status, then git commit -m 'Add milk to the list'"],
    setup=crowd_setup, verify=crowd_verify,
)


# --- Branch Bramble: a branch for an idea, so main stays as it is -------------------------------------

def bramble_setup(work, rng):
    repo(work)
    (work / "app.txt").write_text("version 1\n")
    commit(work, "First version", "app.txt")
    branch = rng.choice(("try-ideas", "new-ideas", "experiment", "sketch"))
    (work / "idea.txt").write_text(f"What if we added {rng.choice(IDEAS)}?\n")
    return {"args": {"branch": branch}}


def bramble_verify(work, meta, value):
    """On the branch, which holds idea.txt in a new commit; main hasn't moved."""
    branch = meta["args"]["branch"]
    here = git(work, "rev-parse", "--abbrev-ref", "HEAD")
    on_branch = git(work, "ls-tree", "--name-only", branch)
    on_main = git(work, "ls-tree", "--name-only", "main")
    main_count = git(work, "rev-list", "--count", "main")
    return (here is not None and here.strip() == branch and on_branch is not None and "idea.txt" in on_branch.split()
            and on_main is not None and "idea.txt" not in on_main.split() and (main_count or "").strip() == "1")


BRANCH_BRAMBLE = Challenge(
    level=1, id="branch_bramble", pet="beaver", tools=("git",), threat="Branch Bramble", requires=["git"], fix=True,
    after=("commit_crowd",),
    task="The Branch Bramble grows wild ideas. Keep main as it is: create a branch named {branch}, switch to it, "
         "and commit idea.txt there. Then: verify",
    help="Here, look at git switch --help: one option creates the branch as it switches.",
    hints=["A branch is a separate line of commits: what you commit on it doesn't change main. git switch -c "
           "NAME creates a branch and moves onto it (older git: git checkout -b NAME). git branch shows "
           "where you are, with a *.",
           "Try: git switch -c {branch}, then git add idea.txt and git commit -m 'An idea'."],
    setup=bramble_setup, verify=bramble_verify,
)


# --- Conflict Chimera: two branches changed the same line --------------------------------------------

def conflict_setup(work, rng):
    repo(work)
    (work / "menu.txt").write_text("Starter: soup\nDessert: fruit\n")
    commit(work, "Menu", "menu.txt")
    git(work, "switch", "-q", "-c", "chef") or git(work, "checkout", "-q", "-b", "chef")
    (work / "menu.txt").write_text("Starter: soup\nDessert: chocolate cake\n")
    commit(work, "Chef's dessert", "menu.txt")
    git(work, "switch", "-q", "main") or git(work, "checkout", "-q", "main")
    (work / "menu.txt").write_text("Starter: soup\nDessert: apple pie\n")
    commit(work, "Grandma's dessert", "menu.txt")
    git(work, "merge", "chef")                                  # stops on the conflict, on purpose
    return {}


def conflict_verify(work, meta, value):
    """The merge is done (two parents, nothing left in progress), with both desserts and no markers."""
    parents = git(work, "rev-list", "--parents", "-n", "1", "HEAD")
    status = git(work, "status", "--porcelain")
    menu = (work / "menu.txt").read_text() if (work / "menu.txt").is_file() else ""
    markers = any(line.startswith(("<<<<<<<", "=======", ">>>>>>>")) for line in menu.splitlines())
    return (parents is not None and len(parents.split()) == 3 and status == "" and not (work / ".git" / "MERGE_HEAD").exists()
            and "chocolate cake" in menu and "apple pie" in menu and "soup" in menu and not markers)


CONFLICT_CHIMERA = Challenge(
    level=2, id="conflict_chimera", pet="beaver", tools=("git",), threat="Conflict Chimera", requires=["git"],
    fix=True, after=("branch_bramble",),
    task="The Conflict Chimera has two heads: you merged the branch chef into main, and both changed the "
         "dessert line of menu.txt. Git stopped and left markers in the file.\nKeep both desserts, remove the "
         "markers and finish the merge. Then: verify",
    help="Here, look at git merge --help, the part HOW TO RESOLVE CONFLICTS.",
    hints=["cat menu.txt: between <<<<<<< and ======= is your side (main), between ======= and >>>>>>> the "
           "other branch's. Git can't choose for you. Edit the file so it reads the way you want, without "
           "the three marker lines, then tell git it's settled: git add menu.txt.",
           "Open {editor} menu.txt, keep the two Dessert lines and delete the <<<<<<<, ======= and >>>>>>> "
           "lines ({save_keys}). Then: git add menu.txt and git commit (the message is ready, or add "
           "-m 'Merge chef')."],
    setup=conflict_setup, verify=conflict_verify,
)


# --- Revert Revenant: undo a shared commit without rewriting history ---------------------------------

def revenant_setup(work, rng):
    repo(work)
    grams = rng.choice((100, 150, 200))
    (work / "recipe.txt").write_text(f"Flour: 250 g\nSugar: {grams} g\n")
    commit(work, "Recipe", "recipe.txt")
    (work / "recipe.txt").write_text(f"Flour: 250 g\nSalt: {grams} g\n")
    commit(work, "Tweak the recipe", "recipe.txt")
    bad = (git(work, "rev-parse", "HEAD") or "").strip()
    (work / "notes.txt").write_text("Bake 30 minutes at 180 degrees.\n")
    commit(work, "Add baking notes", "notes.txt")
    return {"shared": (git(work, "rev-parse", "HEAD") or "").strip(), "bad": bad, "grams": grams}


def revenant_verify(work, meta, value):
    """The shared commits are all still in the history (nothing rewritten), a revert of the bad one puts
    the sugar back (a fix by hand would hide which commit it undoes), the notes stay, nothing uncommitted."""
    kept = subprocess.run(["git", "merge-base", "--is-ancestor", meta["shared"], "HEAD"], cwd=work,
                          capture_output=True).returncode == 0 if meta.get("shared") else False
    count = git(work, "rev-list", "--count", "HEAD")
    recipe = git(work, "show", "HEAD:recipe.txt") or ""
    files = (git(work, "ls-tree", "--name-only", "HEAD") or "").split()
    reverts = f"This reverts commit {meta.get('bad')}" in (git(work, "log", "-1", "--format=%B") or "")
    return (kept and reverts and (count or "").strip() == "4" and f"Sugar: {meta['grams']} g" in recipe and "Salt" not in recipe
            and "notes.txt" in files and git(work, "status", "--porcelain") == "")


REVERT_REVENANT = Challenge(
    level=2, id="revert_revenant", pet="beaver", tools=("git",), threat="Revert Revenant", requires=["git"],
    fix=True, after=("branch_bramble",),
    task="The Revert Revenant slipped a bad commit into main: \"Tweak the recipe\" put salt where the sugar "
         "was. Everyone already pulled main, and a good commit came after it.\nUndo the bad commit without "
         "rewriting the history. Then: verify",
    help="Here, look at git revert --help: it undoes a commit with a new one.",
    hints=["git log --oneline shows the history, newest first: find the bad commit. git reset would remove "
           "commits from main, and everyone who pulled them would be out of step. git revert adds a new "
           "commit that does the opposite of the bad one, so the history only grows.",
           "Try: git log --oneline, then git revert --no-edit followed by the bad commit's hash (here also "
           "HEAD~1, the commit before the newest one)."],
    setup=revenant_setup, verify=revenant_verify,
)

ALL = [COMMIT_CROWD, BRANCH_BRAMBLE, CONFLICT_CHIMERA, REVERT_REVENANT]


# --- the chest after the road lesson "git" ----------------------------------------------------------

def first_setup(work, rng):
    repo(work)
    (work / "map.txt").write_text("The treasure is under the old oak.\n")
    return {}


GIT_CHEST = trial("trial_first_commit", 1, "This chest is a git repository with one new file, map.txt. Save it "
                  "in a first commit (any message). Then: verify",
                  ["git status shows map.txt as untracked. git add puts it in the next commit, git commit -m "
                   "'message' makes the commit, git log shows it.",
                   "Try: git add map.txt && git commit -m 'Add the map'"],
                  first_setup, lambda w, m, v: (git(w, "ls-tree", "--name-only", "HEAD") or "").split() == ["map.txt"]
                  and git(w, "status", "--porcelain") == "", requires=["git"], teaches=["git"])
CHESTS = [GIT_CHEST]
