# AGENTS.md

## Repository safety rules — mandatory

**Branch protection is a hard requirement, not a workflow preference.**

1. Never modify `main` by transferring, copying, merging, cherry-picking, recreating, or manually reimplementing changes from another branch unless the user explicitly authorizes that specific transfer into `main`.
2. Authorization must be clear and unambiguous. Requests such as "fix this", "implement this feature", "use the tested solution", "finish the task", "commit the changes", or "the test branch works" do NOT authorize modifying `main` using changes from another branch.
3. Before any cross-branch transfer into `main`, explicitly identify the source branch, target branch (`main`), and changes to be transferred. Ask the user for confirmation and wait for their response.
4. Never infer authorization from technical readiness, successful tests, previous discussions, or the fact that a solution has already been implemented in a working branch.
5. If the requested target branch is ambiguous, ask the user. Do not silently default to `main`.
6. Do not bypass these rules by manually copying code instead of performing a Git merge or cherry-pick.
7. Reading, comparing and reviewing branches is allowed without approval. Modifying `main` using changes from another branch is not.
8. Before any GitHub write operation, verify that the destination branch matches the user's authorization.
9. Never create or use a repository fork without the user's explicit permission.

**When in doubt, stop and ask.**

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

Before PATCH, identify the target Git branch and verify that the requested changes are authorized for that branch. If the target branch is unclear, ask before modifying repository files.

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

## Architectural decisions

When a task results in a significant architectural or design decision, proactively tell the user that it may be worth recording in `gpt_context/DECISIONS.md`.

Do not update `DECISIONS.md` automatically unless the user explicitly approves it.

Examples include:

- changing module responsibilities or boundaries;
- introducing or removing an architectural pattern;
- changing important interfaces between modules;
- choosing a long-term approach when multiple alternatives exist;
- establishing a project-wide development or processing rule;
- accepting an important architectural tradeoff.

Do not suggest a `DECISIONS.md` entry for routine bug fixes, minor implementation details, formatting, or temporary experiments.

## Important project invariants

A failure while processing one news item must **not terminate the entire processing loop**.

Cleanup of the downloaded `.eml` and `extracted_images/` must happen even when processing fails.

VK objects may occur inside nested `attachments`. Preserve recursive attachment handling when modifying VK processing.

`main.py` is the orchestration layer; domain-specific parsing, VK processing and WordPress logic should remain in their relevant modules.

## Git

GitHub is the canonical repository for the source code.

**Do not transfer code or other changes from test/working branches into `main` without the user's explicit instruction.**

- A request to write code, test it, or commit it is not permission to merge into `main`.
- Never merge, cherry-pick, or otherwise bring a test/working branch into `main` on your own initiative.
- Once changes are ready, report the branch and commit, then wait for the user's direct approval before updating `main` with those changes.

Commit meaningful, reviewable states. Avoid unrelated changes in the same commit.

Never commit secrets or local-only configuration.

Never create or use a GitHub fork of this repository unless the user explicitly asks you to do so.

Do not treat a fork as a fallback when direct changes to the repository or branch are unavailable. Ask the user before creating a fork.

## Environment

The project is developed on Windows with Python 3.13. Keep compatibility with the existing environment unless a task explicitly requires otherwise.
