# Questions for `bashou adventure`

Monsters and bosses ask multiple-choice questions on a topic. Questions are plain JSON files, so you
don't need to touch any code. Each topic has levels: the first time you take a path it's level 1,
after beating its boss level 2, and so on. More questions, and new levels, are very welcome.

Questions may be about tools the player hasn't installed yet: that's how they discover them.

## Where

`bashou/adventure/questions/en/<topic>.json`. Topics: `bash`, `linux`, `python`, `rust`, `c`,
`debian`, `rocky`, `cicd`, `systemd`, `logic` (coding logic for beginners, in short Python-like
pseudocode). Translations go in `questions/<lang>/<topic>.json` (same ids, levels and
answer positions); a missing translation falls back to English. See [translations.md](translations.md).

```json
{"id": "linux-1-11", "level": 1,
 "q": "A process ignores Ctrl+C. What do you try before kill -9?",
 "choices": ["kill PID, which lets it clean up", "A reboot", "Deleting its program file", "Nothing: -9 first is fine"],
 "answer": 0,
 "explain": "kill PID politely asks the program to stop: it can save its work and close its files. kill -9 stops it at once, with no cleanup: half-written files, leftover lock files. Try kill first, wait a few seconds, and keep -9 for when it really won't stop."}
```

- `id`: `<topic>-<level>-<number>`, unique. `answer`: the index (0-3) of the right choice. The game
  shuffles the choices anyway, so the right one can stay first.
- `explain`: shown after the answer, right or wrong, under the right choice. It's what people
  remember, so write it like a teacher (see below): 2 to 4 short sentences, at most 400 characters.

## A good question

- **Foundations, not recitation** (owner): ask what a file or a command is *for*, or how to recognize
  something in real output — spotting a `$6$…` hash is useful, reciting the field order of
  /etc/passwd is not. The details (field order, option lists, the neighbouring commands) belong in
  `explain`, which is read once the answer is given.
- **Long-term value** (owner): each question should leave a habit that holds up in automation and security —
  why a script uses `set -e` or `mkdir -p`, what a listening `0.0.0.0` means, why a secret never goes in a
  commit. Prefer "what goes wrong / what do you check first / what does this output tell you" over "which
  command does X". Trivia (codenames, acronyms, which function prints) has no place.
- **Everyday situations**: trusting a repository key, finding which package owns a file, finishing a
  half-done upgrade. A few "build the command, the help is there" questions are welcome; niche flags
  and trivia are not.
- **One right answer**, and three wrong ones that look plausible (no joke choices).
- **Teacher style** (owner, after players found the answers too terse): players are often beginners.
  The question gives enough context to picture the situation (who, where, what just happened). The
  explanation, in plain words: (1) why the right answer is right, (2) what the tempting wrong answer
  really does or why it doesn't fit, (3) what to do or remember next. Explain a term the first time it
  appears (`df` = disk free); no unexplained jargon (UID, SIGTERM…) at level 1.
- **Fits the screen**: 150 characters for the question, 60 per choice, 400 for the explanation.
- **Level 1**: everyday basics. **Level 2**: things you meet after a few months. **Level 3**: the
  details that bite in production.
- **Your own words**: don't copy questions from quizzes, certifications or courses.
- Check it's true today (versions change: say which tool or distro when it matters).

## Check

```bash
python3 -m unittest tests.test_adventure    # every bank: 4 different choices, valid answer, lengths, ids
```

Or open an issue with the *Adventure question* template if you'd rather not touch JSON.
