# Git Strategy

Purpose: define how multiple agents collaborate without conflicting commits.

## Branching
- Use a short-lived branch per agent (e.g., `mimicry-model/<topic>`, `hands-eyes/<topic>`).
- Rebase or merge into `main` only after local verification or agreed checkpoints.

## Commit Rules
- Small, single-topic commits only.
- Prefix commit messages with area: `mimicry:`, `hands:`, `docs:`, `exec:`.
- Do not amend another agent’s commit.

## Coordination
- Announce branch name + focus in `docs/HANDS_TALK.md`.
- If touching shared files, post a heads-up before editing.
- Resolve conflicts by the agent who owns the module; ask if uncertain.

## Local Only
- Commits remain local unless explicitly approved to push.
