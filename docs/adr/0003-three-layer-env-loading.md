# 0003 - Three-layer env loading with secrets outside the workspace

- Status: Accepted
- Date: 2026-08-18

## Context

The app and the pipeline notebooks need configuration (endpoints, model
names, chunking parameters, RRF weights, …) and one secret (the LLM API
key). The workspace is shared with AI agents and the repository is public —
the key must never be visible from the repo or the working tree.

## Decision

Configuration is loaded in three layers, later layers win:

1. `.env.example` — committed defaults (the documented configuration
   surface, every parameter with a comment).
2. `.env` — local overrides, git-ignored.
3. `~/.config/rag-quote-history/secrets.env` — **secrets only**, outside
   the workspace, `chmod 600`.

Both the app (`app/src/rag_system/config.py`) and the notebook setup cells
use the same loading order, so pipeline and app always agree.

## Consequences

- The API key never enters the workspace, the repo, or any agent's file
  access — external agents with repo access cannot see it.
- `.env.example` doubles as the configuration reference; a fresh clone is
  runnable after `cp .env.example .env` plus one secrets file.
- Values are read once at startup — index or endpoint changes require an
  app restart (documented behavior, not a bug).
