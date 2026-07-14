# ADR 2026-07-14 — Exclude `cad_designer/` from SonarCloud analysis

- **Status:** Accepted
- **Date:** 2026-07-14
- **Deciders:** Marc Szymanski (maintainer)

## Context

The SonarCloud quality gate on `main` went to **ERROR** (`new_reliability_rating`,
`new_security_rating`, `new_coverage`). Investigation showed the gate-breakers are
**32 findings, ~18 of them inside `cad_designer/`**, including 2 BLOCKER and 2 further
vulnerabilities plus assorted MAJOR/MINOR bugs (float-equality, always-false
conditions, useless self-assignments, non-hashable expressions).

`git blame` confirmed these are **latent, long-standing issues** (2024-04 … 2025-05),
not regressions from recent work. They only surfaced now because `cad_designer` is in
`sonar.sources` and the SonarCloud new-code baseline swept them into the gate.

`cad_designer/` is **deliberately read-only** (see CLAUDE.md and the
`feedback_cad_designer_locked_fragile` memory): it is fragile geometry/topology code
with subtle CadQuery/OCCT behaviour. The maintainer's explicit direction is that this
code must **not be modified** to satisfy a linter — a plausible-looking cleanup can
silently change geometry output, and that risk outweighs a green gate.

Concrete example of the fragility: `WingConfiguration._set_standard_spare_origin_vector`
has a genuinely dead `elif spare.spare_vector is None` branch (the "perpendicular spare"
fallback), unreachable since a `spare_position_factor = 0.25` default was prepended on
2024-04-10. It is a real (if low-impact) logic change, yet we deliberately leave it
untouched — exactly the kind of finding that must not force a code edit.

## Decision

Exclude `cad_designer/**` from SonarCloud analysis via `sonar.exclusions` in
`sonar-project.properties`. `app/` and `frontend/` remain fully analysed and gated.

## Consequences

**Positive**
- The `main` quality gate reflects only code we are willing and able to change
  (`app/`, `frontend/`), so a red gate is again an actionable signal.
- No pressure to edit fragile, locked geometry code to chase a green gate.

**Negative / trade-off**
- SonarCloud will **no longer flag new issues introduced in `cad_designer/`**. If that
  code is ever unlocked and actively developed, this exclusion should be revisited so
  new work there is covered again.
- Coverage for `cad_designer/` no longer counts toward the gate (it was low anyway).

**Mitigations**
- `cad_designer/` is stable and rarely changed; new geometry goes through *new* Creators
  (allowed by CLAUDE.md), which can be added under a path that is analysed if desired.
- The pytest suites (`cad_designer/tests/`) continue to run in CI independently of Sonar.

## Alternatives considered

1. **Fix the 18 findings in place** — rejected: violates the read-only/fragile rule; high
   risk of silently changing geometry behaviour.
2. **Mark each as "won't fix" in the SonarCloud UI** — rejected: not version-controlled,
   not reviewable, must be repeated for every new finding.
3. **Leave the gate red and ignore it** — rejected: a permanently-red gate trains the team
   to ignore it, masking future *actionable* `app/`/`frontend/` regressions.
