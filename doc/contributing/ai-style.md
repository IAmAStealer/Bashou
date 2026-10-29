# AI style: using AI tools with judgment

Bashou teaches AI tools so that the player stays the pilot: what the model sees (its context), how to
make it plan before it codes, and how to check what it did. The facts about tools change fast, so
every one names its tool and comes from that tool's own docs, and the habits must hold for any tool.

This file is the checklist for every AI sample in Bashou: the lessons `ai_context` and `ai_plan`, the
ai adventure questions, their hints. The `ai-judge` agent (`.claude/agents/ai-judge.md`) applies it
after each change, and `tests/test_ai_style.py` checks this file.

Each rule has an id, used in reviews. A sample that breaks a rule on purpose (a wrong choice) is
marked ✘ and followed by the right form. The right answer and its explanation must follow the rules.

Facts are checked against the tools' official docs (code.claude.com, agents.md, the vendor's pages)
and security references (OWASP), never from memory. A number that changes (window sizes, prices,
limits) is given as an example ("for example, 200 000 tokens"), never as a constant.

| Id | Rule | Why | Source |
|---|---|---|---|
| A1 | A tool fact names its tool and comes from its docs: a command (`/clear`, `/compact`), a key (Shift+Tab), a file (`CLAUDE.md`, `AGENTS.md`), a mode. The habit is said for every tool ("other tools have a new chat button"). | Tools change and differ; players use several. | [Claude Code: memory](https://code.claude.com/docs/en/memory), [AGENTS.md](https://agents.md/) |
| A2 | The model only sees its context window: instructions, messages, answers, files read, command outputs. It has no memory between sessions except files the tool loads. Sizes are examples. | "It knows my project" is the root of most surprises. | [Claude Code: memory](https://code.claude.com/docs/en/memory), [Anthropic: context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows) |
| A3 | An instruction file (`CLAUDE.md`, `AGENTS.md`) is context, not enforcement; a rule that must always hold goes in permissions or a hook. Keep it short (Claude Code advises under 200 lines). | A model may not follow advice; a hook always runs. | [Claude Code: memory](https://code.claude.com/docs/en/memory), [Claude Code: hooks](https://code.claude.com/docs/en/hooks-guide) |
| A4 | No secret in anything the model reads (prompts, instruction files, logs pasted in): it is sent to the provider and may land in the history. | Leaks through context. | [OWASP LLM02:2025 Sensitive Information Disclosure](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/) |
| A5 | Output is checked before it's kept: read the diff, run the tests yourself, ask about removed tests. The model can be confident and wrong; a package or API it names may not exist. | Misinformation, and hallucinated package names that attackers register. | [OWASP LLM09:2025 Misinformation](https://genai.owasp.org/llmrisk/llm092025-misinformation/), [OWASP LLM05:2025 Improper Output Handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/) |
| A6 | Least agency: give the tool only the access and commands it needs; no production keys; approve risky actions. | An agent with too much power does damage when wrong or tricked. | [OWASP LLM06:2025 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/), [Claude Code: permissions](https://code.claude.com/docs/en/permissions) |
| A7 | Text the model reads from outside (a web page, an issue, a file from someone else) can carry instructions: it is data, and the player stays wary of what it makes the tool do. | Prompt injection. | [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) |
| A8 | Plan before code for anything bigger than a small fix; read the plan like a colleague's; work in small checked steps with commits. Plan mode is named per tool (Claude Code: Shift+Tab or `--permission-mode plan`). | A wrong plan costs a sentence, wrong code an afternoon. | [Claude Code: common workflows, plan before editing](https://code.claude.com/docs/en/common-workflows#plan-before-editing), [Claude Code: best practices](https://code.claude.com/docs/en/best-practices) |
| A9 | Long sessions degrade: one task per session, start fresh with a short summary when stuck; decisions live in a file, not in the chat. | Old failed tries pull the model back; summaries drop details. | [Claude Code: best practices](https://code.claude.com/docs/en/best-practices) |
| A10 | No claim about how a model works inside beyond what the docs say (no "it searches the web", "it understands", "it learns from you" unless the tool does that and says so). Bashou says tokens are "pieces of text", not words: a token can be a word, part of one or a sign. | Players build their trust on these words. | [Anthropic: tokens and context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows) |
