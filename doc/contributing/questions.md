# Questions for `bashou adventure`

Monsters and bosses ask multiple-choice questions on a topic. Each topic has levels: the first time
you take a path it's level 1, after beating its boss level 2, and so on. More questions, and new
levels, are very welcome.

## Where

`bashou/adventure/questions/en/<topic>.json`. Topics: `bash`, `linux`, `python`, `rust`, `c`,
`debian`, `rocky`, `cicd`. Translations go in `questions/<lang>/<topic>.json` (same ids); a missing
translation falls back to English.

```json
{"id": "linux-2-11", "level": 2,
 "q": "Which command shows the last boot's kernel messages?",
 "choices": ["journalctl -k -b", "cat /boot/log", "dmesg --all-boots", "uname -m"],
 "answer": 0,
 "explain": "-k keeps kernel messages, -b this boot (dmesg works too)."}
```

- `id`: `<topic>-<level>-<number>`, unique. `answer`: the index (0-3) of the right choice. The game
  shuffles the choices anyway, so the right one can stay first.
- `explain`: one short sentence shown after the answer, right or wrong. It's what people remember.

## A good question

- **One right answer**, and three wrong ones that look plausible (no joke choices).
- **Short**: 110 characters for the question, 60 per choice (it must fit a small terminal).
- **Level 1**: everyday basics. **Level 2**: things you meet after a few months. **Level 3**: the
  details that bite in production.
- **Your own words**: don't copy questions from quizzes, certifications or courses.
- Check it's true today (versions change: say which tool or distro when it matters).

## Check

```bash
python3 -m unittest tests.test_adventure    # every bank: 4 different choices, valid answer, lengths, ids
```

Or open an issue with the *Adventure question* template if you'd rather not touch JSON.
