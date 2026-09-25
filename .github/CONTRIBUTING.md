# Contributing

Ideas, bug reports, pixel art, translations, questions and security challenges are welcome.

Most contributions don't need any code: you edit a JSON file (or draw PNGs) and run a check.

| You want to… | You edit | Guide |
|---|---|---|
| Translate the game | `bashou/locales/<lang>.json` | [translations.md](../doc/contributing/translations.md) |
| Translate adventure questions | `bashou/adventure/questions/<lang>/<topic>.json` | [translations.md](../doc/contributing/translations.md) |
| Write or fix a lesson | `bashou/lesson/en/<id>.json` | [lessons.md](../doc/contributing/lessons.md) |
| Add adventure questions | `bashou/adventure/questions/en/<topic>.json` | [questions.md](../doc/contributing/questions.md) |
| Improve a pet's pixel art | `bashou/pets/<pet>.json` | [pixel-art.md](../doc/contributing/pixel-art.md) |
| Draw bigger pets by hand (16/32/64 px, no code, no AI) | `art/<pet>/<size>/<pose>.png` | [pixel-art.md](../doc/contributing/pixel-art.md) |
| Write a security challenge | Python (a small setup function) | [security-challenges.md](../doc/contributing/security-challenges.md) |
| Package releases (apt, dnf) | `tools/package.py`, `.github/workflows/packages.yml` | [packaging.md](../doc/contributing/packaging.md) |

Translating with an AI agent: see [doc/agents/translation.md](../doc/agents/translation.md).

Bugs and ideas: [open an issue](https://github.com/IAmAStealer/Bashou/issues/new/choose) and pick a form
(bug, idea, lesson, adventure question, security challenge). Not comfortable with JSON? The *Adventure
question* and *Lesson* forms work too. Security problems go through the
[private report](https://github.com/IAmAStealer/Bashou/security/advisories/new), never a public issue.

Everything you send must be yours to share (no copies from games, CTFs or other projects), and is
shared under the project's MIT license. Before a pull request, run `python3 -m unittest`.

**Working with an AI is welcome** (Bashou itself is built that way, see [how it started](../doc/STORY.md)),
with one exception: the **`art/` folder and large sprites** (`bashou/pets/large/`) are for people, drawn by
hand, no AI. `art/` needs no programming: draw PNG files, drop them in a pull request, and we turn them into
the game's files. Sprites that go straight into the game (`bashou/pets/<pet>.json`, 17 × 12) may be drawn
with an AI and are reviewed by hand; new pets are fine too, and best as a **whole set**: the pet and its achievements, a fight with its hints, a
lesson that lists the fight, and adventure questions (see [curriculum.md](../doc/contributing/curriculum.md)). Whatever the tool, you're responsible for what
you send: read it, test it, and check its facts.

Everyone follows the [code of conduct](CODE_OF_CONDUCT.md): kind and patient, beginners first.
