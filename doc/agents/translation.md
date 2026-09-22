# Agent instructions: translating Bashou

For contributors who translate Bashou with an AI agent (Claude Code, Codex, Cursor…). Point your
agent at this file, for example with a line in your `CLAUDE.md` or `AGENTS.md`:

```
Follow doc/agents/translation.md. I am the native speaker; ask me before choosing names.
```

The human guide is [doc/contributing/translations.md](../contributing/translations.md). This file adds
how an agent should work, based on how the French translation was made and reviewed.

## Your role

You translate; the human decides. They are a native speaker of the target language, you may not be.
Draft everything, but never settle a name, a pun or a tone on your own: ask. A game translation is
judged on its names and jokes, and those are the parts you'll get wrong without context.

## What to edit (JSON only, no code)

| What | File |
|---|---|
| Every message: menus, pet lines, hints, achievements, fights, settings, adventure names | `bashou/locales/<lang>.json` |
| Adventure questions | `bashou/adventure/questions/<lang>/<topic>.json` |

Setup, once:

```bash
echo '{"@language": "Deutsch"}' > bashou/locales/de.json   # the language's name, in that language
python3 -m bashou.i18n                                      # fills in every message to translate, empty
```

Rerun `python3 -m bashou.i18n` any time: it adds new messages, drops old ones, keeps translations,
and prints how many are done. An empty value shows the English, so partial work can ship.

## Rules the tests enforce

Run `python3 -m unittest tests.test_i18n tests.test_adventure` after each batch.

- Keys are the English text: never change a key.
- Keep every `{placeholder}` (`{name}`, `{count}`…); you may move it.
- Pet, stage and form names must fit **16 characters** (the swap board cuts them).
- Question files keep the same `id`, `level` and `answer`, and the choices in the same order
  (`answer` is a position). Translate only `q`, `choices` and `explain`.
- Valid JSON in UTF-8: write accented letters as they are (`é`), not as `\u` escapes.

## Rules the tests can't check

- **Never translate commands**: anything in backticks, command names, flags, file names, `bashou …`.
- **Context first.** The same English word can need different translations. Before translating a
  message, find where it's used: `grep -rn "the message" bashou/`. A name used inside sentences
  (a threat: "{threat} arrives!") needs a form that works there.
- **Short.** Most lines go in a small speech bubble. Stay close to the English length.
- **One word per concept, everywhere.** Before starting, agree on a glossary with the human and keep
  it: companion/pet, achievement, level, stage, threat, fight, adventure, boss, chest. For French it
  was: compagnon, succès, niveau, forme (for a stage), menace, combat, aventure, boss, coffre.
- **Tone.** Pets talk to the player casually. Ask which form of address to use (French uses `tu`).
- **Names inside sentences.** If your language needs articles or cases, translate threats and bosses
  as common nouns with their article and let the code capitalize a sentence's first letter
  (`i18n.cap()`), as French does: `"Log Hydra": "une hydre des logs"`, used as "Une hydre des logs
  arrive !".
- **Puns don't carry over.** Replace an English pun with one that works in your language, or drop
  it. And the other way round: a pun that only works in your language must not change the art or
  the English (a French "porc-épic / épique" joke was dropped for that reason).

## How to work with the human (this is what worked)

1. **Agree on the glossary and the tone** before translating anything (one short question each).
2. **Translate in batches** by area: interface, pet lines, achievements, fights, adventure, then
   the question banks one topic at a time. Run the tests after each batch.
3. **Review names one by one, not as a long list.** A list of 100 names is too long to check. Ask
   about a few at a time (four is good), each with 2–3 concrete proposals and why:
   - pets and their three stages (a stage-3 form is the rare, legendary one: make it feel special);
   - achievements whose literal translation is wrong, not a real word, or has a bad double meaning;
   - threats, bosses, chapters and places.

   Only ask about the doubtful ones, then show the rest in one compact list so the human can object.
4. **Tell the human where to see it**: `BASHOU_LANG=<lang> bashou talk`, `bashou achievements`,
   `bashou swap` (names on the board), `bashou adventure`.
5. **Write down every idea the human gives** (new stages, variants, jokes) in the pull request or an
   issue, even the ones you don't implement: they are the owner's ideas for later.

## Before the pull request

```bash
python3 -m bashou.i18n            # 100% translated? (partial is fine too)
python3 -m unittest               # everything passes
```

Everything sent must be the contributor's own work, shared under the project's MIT license. Say in
the pull request that an agent helped, and that a native speaker reviewed it.
