# Contributing

Ideas, bug reports, pixel art, translations, questions and security challenges are welcome.

Most contributions don't need any code: you edit a JSON file (or draw PNGs) and run a check.

| You want to… | You edit | Guide |
|---|---|---|
| Translate the game | `bashou/locales/<lang>.json` | [translations.md](../doc/contributing/translations.md) |
| Translate adventure questions | `bashou/adventure/questions/<lang>/<topic>.json` | [translations.md](../doc/contributing/translations.md) |
| Add adventure questions | `bashou/adventure/questions/en/<topic>.json` | [questions.md](../doc/contributing/questions.md) |
| Improve a pet's pixel art | `bashou/pets/<pet>.json` | [pixel-art.md](../doc/contributing/pixel-art.md) |
| Draw bigger pets (16/32/64 px) | `art/<pet>/<size>/<pose>.png` | [pixel-art.md](../doc/contributing/pixel-art.md) |
| Write a security challenge | Python (a small setup function) | [security-challenges.md](../doc/contributing/security-challenges.md) |

Translating with an AI agent: see [doc/agents/translation.md](../doc/agents/translation.md).

Bugs and ideas: open an issue. Not comfortable with JSON? The *Adventure question* issue template
works too.

Everything you send must be your own work (no copies from games, CTFs or other projects), and is
shared under the project's MIT license. Before a pull request, run `python3 -m unittest`.
