# Claude Code Configuration

This folder contains Claude Code configurations, agents, commands, and hooks.

## Agents (`agents/`)

| Agent | Purpose |
|-------|---------|
| `code-base-explorer` | Serena LSP-backed codebase exploration |
| `code-reviewer` | Project-specific code review orchestrator (Serena + SonarQube + language reviewers) |
| `python-reviewer` | Python-specific code review (FastAPI, Pydantic, conventions) |
| `typescript-reviewer` | TypeScript/React code review (Next.js App Router, frontend conventions) |
| `work-orchestrator` | Supercycle work orchestration |

## Commands (`commands/`)

### Supercycle Commands (Primary workflow)
| Command | Usage |
|---------|-------|
| `/supercycle:status` | Project health dashboard |
| `/supercycle:ticket` | Brainstorm + create refined GH Issue |
| `/supercycle:work` | Full cycle: brainstorm, implement, review, merge |
| `/supercycle:bug` | Bug intake: investigate, ticket, TDD fix, merge |
| `/supercycle:implement` | Skip brainstorming, parallel implementation |
| `/supercycle:review` | Dispatch code review agents on open PRs |
| `/supercycle:fix` | Fix review findings on PR branches |
| `/supercycle:merge` | CI check + sequential merge with rebase |

### Utility Commands
| Command | Usage |
|---------|-------|
| `/utility:commit` | Create a well-formatted commit |
| `/utility:format` | Format code files |
| `/utility:investigate` | Investigate a topic, bug, or codebase area |
| `/utility:lint` | Run linter with optional auto-fix |
| `/utility:refactor` | Safely refactor code |
| `/utility:review` | Quick code review |
| `/utility:security-review` | Security analysis |
| `/utility:test` | Run tests with analysis |

### Architecture Commands
Arc42 documentation and ADR workflows.

## Rules (`rules/`)

- `git-safety.md` — Git commit and branch safety rules
- `python-conventions.md` — Python code style guidelines
- `security.md` — Security best practices

## Hooks (`hooks/`)

- Pre-command: toolchain check, sensitive path guard, tool-use logging
- Post-command: format, lint, issue tracking validation
- Sonar secrets: secret detection in Read/prompt operations
