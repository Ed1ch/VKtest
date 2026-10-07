# AGENTS.md

## Project

VKTest is a Python application that processes incoming email news (`.eml`), extracts text, images and VK links/attachments, processes VK content through the VK API, and publishes the resulting content to WordPress.

Project context is maintained in `gpt_context/`:

- `README.md` — short project overview.
- `ARCHITECTURE.md` — module boundaries and architecture.
- `CONTEXT.md` — current development context.
- `DECISIONS.md` — durable architectural decisions.

## Source of truth

For implementation details, use this priority:

1. Current source code in the repository.
2. `ARCHITECTURE.md` and `DECISIONS.md`.
3. `CONTEXT.md`.
4. Current conversation.

Do not assume that old chat context reflects the current code.

Before making a non-trivial change:

1. Read `gpt_context/ARCHITECTURE.md`.
2. Read `gpt_context/CONTEXT.md`.
3. Read `gpt_context/DECISIONS.md`.
4. Inspect the actual affected source files.
5. Search for usages of functions/interfaces being changed.

## Development workflow

For non-trivial changes use **PLAN -> PATCH -> REVIEW**.

### PLAN

Identify affected modules, interfaces and regression risks. Do not modify code yet when the user asks to review the plan first.

### PATCH

Make the smallest change that solves the task. Do not perform unrelated refactoring.

### REVIEW

Review the diff for regressions, broken contracts, unnecessary complexity and duplicated functionality. Run relevant tests or perform the available targeted checks.

## Development rules

- Prefer small, targeted changes over unnecessary rewrites.
- Preserve existing behavior unless the task explicitly requires changing it.
- Do not silently change architecture or public contracts between modules.
- Search for existing functionality before adding a helper or module.
- Keep modules responsible for their own domain.
- Prefer simple, explicit Python over clever abstractions.
- Do not introduce new architectural patterns, base classes, factories, async code or abstraction layers unless they solve a concrete problem in the current task.
- Do not hardcode credentials, tokens or other secrets.
- Keep temporary files out of Git.
- Update relevant `gpt_context/*.md` files when architecture, important behavior or durable decisions change.
- Do not invent APIs, data structures or project behavior. Inspect the actual code first.
- When uncertain, state the uncertainty rather than guessing.

## Important project invariants

A failure while processing one news item must **not terminate the entire processing loop**.

Cleanup of the downloaded `.eml` and `extracted_images/` must happen even when processing fails.

VK objects may occur inside nested `attachments`. Preserve recursive attachment handling when modifying VK processing.

`main.py` is the orchestration layer; domain-specific parsing, VK processing and WordPress logic should remain in their relevant modules.

## Git

GitHub is the canonical repository for the source code.

Commit meaningful, reviewable states. Avoid unrelated changes in the same commit.

Never commit secrets or local-only configuration.

## Environment

The project is developed on Windows with Python 3.13. Keep compatibility with the existing environment unless a task explicitly requires otherwise.
