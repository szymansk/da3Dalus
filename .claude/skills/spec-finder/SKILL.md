---
name: spec-finder
description: "Resolves a ticket, a feature idea or a set of changed files to the Reversa spec units that govern it, and returns a compact brief — unit paths, the decisions already made, the binding ADRs and any current addenda. Use before brainstorming, planning or reviewing, and whenever someone asks 'what does the spec say about X' or 'which spec covers this file'. Invoked by /supercycle-work's planning phase."
---

# spec-finder

`_reversa_sdd/` holds **11 100+ confidence-marked statements** across 18 modules and 62
use-case units, plus 206 answered validation questions and 25 binding ADRs. Nobody can
read that per ticket, and nobody should: the point of the extraction is that the relevant
slice can be found and handed on **compactly**.

Your job is that slice. You return a brief, not a reading list.

## Non-negotiables

1. **Cite, never paraphrase silently.** Every claim you pass on carries
   `_reversa_sdd/<path>#<section>` or a question id (`Q-WD-1`, `R2-10`). A statement
   without a source is not a finding, it is a guess.
2. **Carry both markers.** Every statement has two axes (`_reversa_sdd/MARKERS.md`):
   *confidence* — 🟢 CONFIRMED, 🟡 INFERRED, 🔴 GAP — and *tense* — **Ist** (true today,
   with `file:line`) or **Soll** (decided, not built, with a GH issue number). Stripping
   the confidence marker turns an inference into a fact; stripping the tense makes a
   planner build against a system that does not exist.
   **A Soll without a ticket number is a finding — report it.** It means a decision has
   no execution path, and nobody will notice it was never built.
3. **Report gaps as findings.** If the spec does not cover the ticket, say so plainly and
   name the nearest unit. A confident-sounding brief over a 🔴 is worse than "not
   specified".
4. **Read narrowly.** `code-analysis.md` is 298 KB and `questions.md` 560 KB. Never read
   either whole — locate line ranges with `grep -n`, then read only those.

## Resolution — three routes, most precise first

### Route A — by file path (most precise)

If the ticket names source files, `traceability/code-spec-matrix.md` maps **file → owning
unit(s)** directly. One row per legacy file, ~460 rows.

```bash
grep -n "app/services/wing_service.py" _reversa_sdd/traceability/code-spec-matrix.md
```

Rows marked 🗑 **slated for deletion** are a finding in themselves: the ticket may be
touching something scheduled for removal. Say so before anything else.

### Route B — by module code

The two-letter codes are the vocabulary shared by the impact matrix and the question ids:

| | | | | | |
|---|---|---|---|---|---|
| **AC** aeroplane-core | **WD** wing-design | **FD** fuselage-design | **AF** airfoil-catalog | **CG** cad-generation | **CT** cad-designer-topology |
| **CP** construction-plans | **VI** openvsp-import | **AA** aero-analysis | **AV** avl-integration | **MS** mission-and-sizing | **MB** mass-and-balance |
| **PT** powertrain | **VS** versioning | **CO** ai-copilot | **MC** mcp-server | **PC** platform-core | **FW** frontend-workbench |

Once you have a module, `spec-impact-matrix.md` §1 gives the **blast radius**: ● direct,
○ indirect, ◐ latent, · none. A change in `AC` reaches almost everything; a change in
`MC` reaches nothing. **Report the ● row** — it is what the planner needs to scope the
work, and it is the single most useful thing this skill produces.

§5 *Change recipes* ("if you change X you must also…") is worth checking for any ticket
that touches a contract surface.

### Route C — by keyword

When neither files nor a module are named, grep the unit requirements for domain terms:

```bash
grep -rln "turbulator" _reversa_sdd/*/*/requirements.md
```

Prefer `requirements.md` over `design.md` — requirements name *what*, design names *how*,
and a ticket is usually about the what. Fall back to `domain.md` for vocabulary.

## What to collect, once the units are known

| Source | What you take |
|---|---|
| `<unit>/requirements.md` | the business rules (`BR-*`) and functional requirements (`RF-*`) the ticket touches, **with their markers** |
| `<unit>/design.md` §Risks and Gaps | anything already known to be wrong there |
| `questions.md` / `questions-round2.md` | **decisions already made** — search the module's question prefix. This is the highest-value section: it stops a planner re-deciding something settled |
| `adrs/README.md` | which ADRs bind. Always check 0019–0023; they apply to every change |
| `addenda/*.md` | what shipped since the extraction. Read **current** ones only — an addendum is current while its `## Vigência` holds a single line (`addenda/README.md`). Two sections outrank the rest: *Decisions now implemented* (it un-flags a ⚠ decided-not-implemented entry — say so, or you will warn a planner about work that already shipped) and *Approved departures* (the unit's rule no longer holds; follow the pointer to the ADR or answer that replaced it) |
| `gaps.md` | whether the area carries a known gap |

**Distinguish decided-from-implemented.** Very many answers are *"decided, not yet
implemented"*. A planner who reads a decision as current behaviour will plan against a
system that does not exist yet. Mark each one.

## Output

Compact. A planner should be able to act on it without opening a spec file — while every
line remains traceable to one.

```markdown
## Spec-Anker — <ticket>

**Units:** `_reversa_sdd/wing-design/spar-sizing/` · `_reversa_sdd/aero-analysis/`
**Blast radius (spec-impact §1):** WD → ● AA, AV, CG, CP · ○ MS

### Governing rules
- 🟢 BR-W3 — spar origins are preserved when `should_preserve_normal_spare` holds
  (`wing-design/spar-sizing/requirements.md#business-rules`)
- 🟡 `moment_fn` carries **un-factored** aerodynamic M(y); `g_limit`/`j` are applied once
  downstream at `spar_solver.py:730` (`Q-WD-8`)

### Already decided — do not re-open
- `Q-WD-8 ②` — the `_MIN_REAR_X_C` clamp order is a confirmed defect; the floor must not
  override the hinge clearance. **Decided, not implemented.**
- `Q-WD-7 ②` — measured: 0 of 11 normal spars fail the preservation predicate.

### Binding ADRs
- ADR 0022 — one authority per user-facing quantity
- ADR 0020 — a clamp or substitution emits a `DesignWarning`

### Gaps in this area
- 🔴 No instrumentation on the `"solid"` path (`Q-…` not addressed by the interview)

### Nothing found
*(if applicable — name the nearest unit and say the area is unspecified)*
```

## When the answer is "the spec does not cover this"

Say it in one line, name the nearest unit, and stop. Do not synthesise a plausible-looking
brief from adjacent material — an invented anchor is worse than no anchor, because the
planner will cite it.
