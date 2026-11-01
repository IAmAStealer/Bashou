# Agent instructions: drawing Bashou's sprites

For contributors who improve or draw Bashou's 17 × 12 sprites with an AI agent (Claude Code, Codex,
Cursor…). Point your agent at this file, for example with a line in your `CLAUDE.md` or `AGENTS.md`:

```
Follow doc/agents/pixel-art.md. I judge every sprite by eye.
```

## Your role

You draw drafts; the human looks at every sprite and decides. Follow the human guide,
[doc/contributing/pixel-art.md](../contributing/pixel-art.md): it holds the format and the rules.

## What you may touch

| Yes | No |
|---|---|
| Pets: `bashou/pets/<pet>.json` (17 × 12) | `art/`: PNGs drawn by hand by people, no AI |
| Enemies: `bashou/enemies/<id>.json` | `bashou/pets/large/`: drawn by people, no AI |

## Check

- Keep every field and pose the original has; `python3 -m bashou.creatures check` must pass.
- Look at each sprite as players see it: `python3 -m bashou.creatures show <id>`.
- Run `python3 -m unittest` before the pull request.
