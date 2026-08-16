# Agent Instructions

<!-- BEGIN:nextjs-agent-rules -->

## Next.js: ALWAYS read docs before coding

Before any Next.js work, find and read the relevant doc in
`frontend/node_modules/next/dist/docs/`. Your training data is outdated —
the docs are the source of truth.

<!-- END:nextjs-agent-rules -->

## Codebase Exploration

Prefer the **code-base-explorer** agent (`.claude/agents/code-base-explorer.md`)
over the generic Explore agent when exploring this codebase. It uses
Serena's LSP-backed symbol tools for semantic navigation (find symbol,
find references, symbols overview) alongside standard Glob/Grep/Read,
giving more accurate results for structural questions.

## Project structure

- `app/` — Python FastAPI backend (dev port **8001**; Docker maps 8086→8000)
- `frontend/` — Next.js frontend (dev port 3000)
- Backend REST API: http://localhost:8001
- Swagger UI: http://localhost:8001/docs · MCP: http://localhost:8001/mcp

## Issue tracking

**GitHub Issues are the single source of truth** (features, bugs, epics). See
`CLAUDE.md` → "Issue Tracking — GitHub Issues" and the `/supercycle-*`
workflow. Persistent cross-session knowledge lives in the auto-memory
(`MEMORY.md`), not in code comments.

## Non-Interactive Shell Commands

**ALWAYS use non-interactive flags** with file operations to avoid hanging on confirmation prompts.

Shell commands like `cp`, `mv`, and `rm` may be aliased to include `-i` (interactive) mode on some systems, causing the agent to hang indefinitely waiting for y/n input.

**Use these forms instead:**
```bash
# Force overwrite without prompting
cp -f source dest           # NOT: cp source dest
mv -f source dest           # NOT: mv source dest
rm -f file                  # NOT: rm file

# For recursive operations
rm -rf directory            # NOT: rm -r directory
cp -rf source dest          # NOT: cp -r source dest
```

**Other commands that may prompt:**
- `scp` - use `-o BatchMode=yes` for non-interactive
- `ssh` - use `-o BatchMode=yes` to fail instead of prompting
- `apt-get` - use `-y` flag
- `brew` - use `HOMEBREW_NO_AUTO_UPDATE=1` env var

## Session Completion

Work is **not complete until `git push` succeeds** — see `CLAUDE.md` →
"Session Completion". Never stop before pushing; never say "ready to push
when you are" — you must push. The `/supercycle-merge` flow handles CI,
rebase, and push for PRs.


---

# Reversa

> Framework de Engenharia Reversa instalado neste projeto.

## Como usar

Use o fluxo adequado no chat:

- `reversa` — descobrir e documentar um sistema existente
- `reversa-new` — criar PRD e specs para um projeto novo
- `reversa-forward` — implementar ou evoluir código a partir das specs
- `reversa-migrate` — planejar a migração de um sistema legado
- `reversa-docs` — gerar o mini-site visual da documentação
- `reversa-agents-help` — consultar o catálogo completo de agentes

## Comportamento ao ativar

Quando o usuário digitar `reversa` sozinho em uma mensagem:

1. Ative o skill `reversa` disponível em `.agents/skills/reversa/SKILL.md`
2. Leia o SKILL.md na íntegra e siga exatamente as instruções do Reversa

## Regra não-negociável

Nunca apague, modifique ou sobrescreva arquivos pré-existentes do projeto legado.
O Reversa escreve apenas em `.reversa/`, `_reversa_sdd/`, `_reversa_docs/` e `_reversa_forward/`.
