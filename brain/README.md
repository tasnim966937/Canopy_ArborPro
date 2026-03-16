# Brain - Persistent Project Memory

This folder is your project's persistent memory for Cursor IDE. It stores context across sessions so the AI knows what you did before, what decisions were made, and where you left off.

## How It Works

A Cursor rule (`.cursor/rules/brain.mdc`) automatically reads this folder at the start of every conversation and uses it to inform responses.

## Files

| File | Purpose | Growth |
|------|---------|--------|
| `project-context.md` | Project name, stack, goals, structure | Written once, rarely updated |
| `progress.md` | Current status, recent work, next steps | Overwritten each update (never grows) |
| `decisions.md` | Key decisions with rationale | Append-only, archived when large |
| `sessions/YYYY-MM-DD.md` | Daily session summaries | One file per day |

## Commands

Say any of these in a Cursor chat:

- **"update brain"** â€” Save current progress snapshot
- **"closing for today"** â€” Full update + write daily session log
- **"brain search [query]"** â€” Search all stored context
- **"brain stats"** â€” Show brain health and metrics
- **"brain recent"** â€” Show last few session summaries
- **"brain ask [question]"** â€” Ask a question answered from stored context
