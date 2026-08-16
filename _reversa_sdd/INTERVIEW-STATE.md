# Interview state — resume here

> Working document for the specification-validation interview that began 2026-08-13.
> Everything already decided lives in [`questions.md`](questions.md) and the
> [ADRs](adrs/). **This file holds only what would otherwise be lost when the
> conversation context is compacted:** the working agreements, and where the interview
> stands.

## How to resume

**The interview is finished — all 206 questions are answered.** Read the *Status* section
below for where things stand and *What is NOT done* for the open work.

If a **third** question round is ever run, the mechanics were: recompute the open set from
`questions.md` (a question is open iff its section still contains the literal
`<!-- fill in here -->`), ask the maintainer **block by block**, write answers into the
matching `## Q-id` section, then fold them into the specs.

> There is no separate "remaining questions" file, deliberately. Two agents once derived
> the open set concurrently and produced disagreeing tallies. `questions.md` is the only
> authority — ADR 0022 applied to this interview's own bookkeeping.

---

## Working agreements (established during the interview — keep these)

1. **Consult the domain experts BEFORE asking the maintainer** an engineering-value
   question. Follow the CLAUDE.md hierarchy: `aircraft-design-scholz` (lead) →
   `aerodynamics-expert` (physics) → `aerosandbox-expert` / `avl-advisor` (tooling) →
   `rc-aircraft-designer` (RC practice only, defers to Scholz). Present the **consensus**
   as a decision-ready recommendation, naming disagreements rather than smoothing them.
2. **Frame everything as hobby RC + UAV, 0.5–15 kg — never transport-category design.**
   A method standard in that literature is not admissible without checking validity at
   this scale. (Roskam's landing model turned out to be calibrated on a *braked Cessna
   172N*.)
3. **Never infer the manufacturing process — ask.** A wrong premise propagates into
   expert briefs and comes back looking sourced. (The wing prints **standing on its root
   rib**, so turbulator height is *not* layer-quantised.)
4. **Look it up rather than asking**, when the question is factual. Two lookup rounds
   answered 21 questions with `file:line` citations and required no maintainer time.
5. **Measure against the real database** when a question is "has this already happened?"
   — all three historical-data risks in `Q-WD-7` turned out to be empty.
6. **Distinguish "constrained" from "determined."** If deriving an answer would mean
   inventing a maintainer preference, ask instead.
7. **Be thorough; do not abbreviate.** The maintainer explicitly asked to work through
   all remaining questions rather than deferring Tier 2/3.
8. **Ask in thematic blocks of 5–8**, not one at a time — but keep genuinely distinct
   decisions separate within the block.
9. When a question's **premise turns out to be wrong**, say so plainly and fix the
   artefacts it reached (answer, consensus document, ADR).

## Status — 2026-08-16, discovery cycle COMPLETE

| | |
|---|---|
| Questions | **206 / 206 answered** (192 round 1 + 14 round 2) |
| Confidence | **84,9 %** (was 74,2 %) — 🟢 8 536 · 🟡 1 777 · 🔴 794 |
| Fold-back | complete: 18 modules, 62 units, both matrices |
| Critical / structural gaps | **0 / 0** |
| Reversa plan | all phases ✅; regression check = no-op (no `_reversa_forward/`) |

**Round 2 lives in [`questions-round2.md`](questions-round2.md)** (R2-01…R2-14), separate
from round 1's `questions.md`.

### What is NOT done

1. **The Reversa↔Supercycle integration is complete — all three seams are built**
   (2026-08-16). See the memory note `project-reversa-supercycle-integration`,
   `.claude/skills/spec-finder/` and [`addenda/README.md`](addenda/README.md).
   **One loose end, carried by seam ③:** nobody writes the
   `Superado pela re-extração de …` line yet — it is the closing step of the next
   `/reversa` re-extraction, because Reversa's own regression check keys on
   `_reversa_forward/`, which this project does not use. Until then every addendum
   counts as current.
2. **Three independent Reversa agents never run:** Data Master, Design System, Visor
   (`.reversa/plan.md`). The first two were judged worthwhile — Design System aligns with
   `Q-FW-4`'s design-system extraction.
3. **The one architectural gap**, recorded in [`architecture.md`](architecture.md) §0:
   a plan returns `dict[ShapeId, Workplane]` (`AbstractShapeCreator.py:49`), so
   build-revealed defects are discarded at the `return`. Closing it touches all 29 Creators
   and `cad_designer`'s freeze (ADR 0002). **Its own design round, not a validation answer.**
4. **A third question round** would be needed for `construction-plans`, `versioning`,
   `platform-core`, `frontend-workbench` — still 12–15 red markers per interview question.

## Artefacts produced by the interview

- **ADRs 0019–0025** (new) + amendments to 0001, 0007, 0010 — now **binding** and wired
  into the supercycle: the *planner* records a `## Binding ADRs` section in the plan,
  implementers inherit constraints through it, and an ADR violation is a **blocking**
  review finding. See `CLAUDE.md` §Architecture and the three supercycle skills.
- `expert-consensus-{sizing,powertrain,aero,turbulator,mass-mission}.md` — sourced
  engineering values.
- **No `expert-consensus-avl-scope.md` exists, deliberately.** The AVL consultation was
  run and its findings are recorded **inside `questions.md` §Q-AV-2 / §Q-AV-3 / §Q-AV-4 /
  §Q-AV-8**, with `file:line` citations into both the application and the **AVL 3.40
  Fortran source**. The agent tasked with writing a separate consensus file went idle
  twice without producing it; the file was not chased further because it would have
  duplicated the record rather than adding to it. Anything the AVL decisions rest on is in
  those four sections.
- `wave2-lookups.md`, `wave3-lookups.md` — 21 factual resolutions with citations.
- `mission-and-sizing/power-loading-presets.md` — derived W/kg presets.
- `question-plan.md`, `remaining-questions.md`, `remaining-after-round2.md` — interview
  planning.
- GitHub issues **#1093** (unauthenticated arbitrary file read via `model_ref`) and
  **#1094** (UI erases `model_ref` on edit).

## Done — the fold-back (kept for the method, not as a task)

All three canonical `reversa-reviewer` steps ran: answers folded into the 18 module and
62 use-case folders, markers reclassified in place, `gaps.md` and `confidence-report.md`
regenerated. **The reclassification rule that matters**, and which an earlier attempt got
wrong: a **derivation is an inference** — only an explicit maintainer decision or a direct
code citation/measurement earns 🟢. Getting this wrong inflates the report precisely on the
answers the reviewer produced itself.

### Cosmetic debt still open

- BR-ID numbering overlaps in `openvsp-import` and `construction-plans`, from two writers
  working the same module concurrently. Content is correct; only the numbering collides.
- Optional: a sharper compression pass over the ADRs (~2 360 lines for 25; the 68-line
  index is what gets read per feature).

## Decisions with unusually wide reach — check new questions against these

- **The entire wing-tessellation subsystem is deleted** (`Q-CG-4`) — both frontend hooks,
  `ViewerPanel`, the three backend services, the `tessellation_cache` table and both
  endpoints. The live 3D path is construction-plan execution only.
  **Not** deleted: `construction_plan_service._tessellate_shapes`, the CAD export/zip path.
- **Component tree is the sole mass authority**; `weight_items` retired (`Q-MB-1`).
- **COTS reference data is corrected, not versioned** — design data is versioned,
  reference data is corrected (`Q-PT-7`).
- **`total_mass_kg` becomes a derived view** of the `mass` design assumption (`Q-MB-7`).
- **MCP will be rebuilt on `copilot_tools`**, not carried forward as a REST wrapper
  (ADR 0025).
