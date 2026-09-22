# Translating Bashou

Everything to translate is in JSON files, so you don't need to touch any code. English is the
source language. A missing or empty translation falls back to English, so a language can ship
half-done.

## What to translate

| What | File | Format |
|---|---|---|
| Messages: menus, pet lines, hints, achievements, fights | `bashou/locales/<lang>.json` | `"English text": "translation"` |
| Adventure questions (monsters and bosses) | `bashou/adventure/questions/<lang>/<topic>.json` | a copy of the English file, translated |

`<lang>` is a two-letter code: `fr`, `de`, `es`…

### Messages: `bashou/locales/<lang>.json`

Each key is the English message, and its value is your translation. Leave a value empty (`""`) and
the English one shows instead.

```json
{
 "@language": "Français",
 "Commands": "Commandes",
 "{name} is now your pet.": "{name} est maintenant ton compagnon.",
 "Try `{example}` (achv: {name})": "Essaie `{example}` (succès : {name})"
}
```

- **Don't change the keys**: they're the English text the game looks up.
- **Keep every `{placeholder}` as it is**, even if you move it around: `{name}`, `{count}`… (a test
  checks it).
- **Don't translate commands** or anything between backticks: `` `grep -r` ``, `bashou fight`,
  file names, flags.
- **Keep it about as short as the English**: many lines go in a small speech bubble.
- `"@language"` is the name of your language, written in that language. It shows up in
  `bashou language`.

### Questions: `bashou/adventure/questions/<lang>/<topic>.json`

Copy the English file (`questions/en/<topic>.json`) to `questions/<lang>/<topic>.json` and translate
`q`, `choices` and `explain` only. Keep `id`, `level` and `answer` as they are, and keep the choices
in the same order: `answer` points at the right one by position. A question missing from your file
shows in English. See [questions.md](questions.md) for what makes a good question.

## Add a new language

1. Create `bashou/locales/<lang>.json` with just its name: `{"@language": "Deutsch"}`.
2. Fill it with every message to translate (empty values):

   ```bash
   python3 -m bashou.i18n        # also shows how much is translated: "de: 0/758 translated"
   ```

3. Translate, as much as you like. The language shows up in `bashou language` right away.

## Context matters

The same English word can need different translations depending on where it shows up. When unsure,
search the code for the message to see where it's used (`grep -rn "the message" bashou/`), or ask in
the pull request. Some tips:

- Pets talk to the player casually: in French, use `tu`, not `vous`.
- Pet names and stage names (`Tadpole`, `Kitsune`) are names: translate them the way a game
  would.
- `achievement`, `level`, `stage`, `threat`, `fight`: use the same word everywhere.

## Check, then send

```bash
python3 -m unittest tests.test_i18n tests.test_adventure   # placeholders, JSON, question ids and answers
BASHOU_LANG=de bashou talk                                  # see your language in the game
```

Then open a pull request. Everything you send must be your own work, shared under the project's MIT
license.
