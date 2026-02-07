# How Claude's Memory System Works

Understanding how Claude stores and uses memory will help you get the most out of the migration.

## Memory Edits

Claude's memory is built on **memory edits** — concise factual statements that persist across conversations. Key constraints:

- **≤200 characters per edit** — each memory must be a short, self-contained fact
- **Max 30 edits total** — you have a limited budget, so prioritize what matters
- **Distilled facts, not conversations** — Claude stores "User is a Python developer" not entire chat logs

## What Makes a Good Memory Edit

**Effective edits:**
- `User is a Staff TPM at LinkedIn's Infrastructure org`
- `User's tech stack: Python, React, FastAPI, Docker, AWS`
- `User prefers concise, direct responses without excessive caveats`
- `User is training for a half-ironman as a vegan athlete`

**Ineffective edits:**
- `User once asked about Python decorators` (too specific, not persistent)
- `User had a conversation about cooking pasta` (not useful context)
- `Remember everything from our chat on Dec 5` (not how memory works)

## How the Migrator Helps

The migrator extracts three types of context:

1. **Personal facts** — self-referential statements like "I'm a developer" or "I live in SF"
2. **Tech stack** — tools and technologies mentioned across conversations
3. **Interest patterns** — topic categories ranked by conversation frequency

These map directly to the kind of distilled facts Claude's memory system is designed for.

## Tips for Importing

1. **Review before importing** — the auto-extraction is heuristic; delete anything inaccurate
2. **Consolidate similar edits** — if you have 5 tech-related edits, combine them into 1-2
3. **Prioritize persistent facts** — focus on things that are true long-term (your role, skills, preferences) over transient details
4. **Save room for future edits** — don't use all 30 slots; leave space for context Claude will learn naturally from new conversations
5. **Use the report for deeper context** — upload `migration_report.md` to Claude for a one-time deep context injection without using memory edit slots
