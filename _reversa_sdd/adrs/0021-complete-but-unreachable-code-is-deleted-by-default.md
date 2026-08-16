# ADR 0021 — Complete but unreachable code is deleted by default; "inert" is forbidden

- **Status:** Accepted — new decision
- **Decided:** 2026-08-13, during the specification validation interview (`P-DEAD-0`)
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (interview answer; 30 catalogued instances, three of them finished safety mechanisms)

## Context

Roughly 30 places hold code that is **complete, sometimes tested, and unreachable**.
Like `P-WARN-0`, this was never asked as one question — it arrived as 30 separate
"dead code: keep or remove?" items, each answered on its own merits, which is how
the third answer ("leave it as is") kept winning. The instances are **not
equivalent**, and the interview separated them into three kinds: **finished safety
or confidence mechanisms sitting switched off** (the AVL replay artefacts `Q-AV-3`;
`validate_geometry` `Q-VI-2`, the gh-647 ±1 % span/area/MAC cross-check against
VSP's own totals, complete and tested but referenced only from its test file;
background re-tessellation `Q-CG-4`); **code with no retention argument at all**
(`Q-CC-16`; `cq_plugins/scaleXyz`, never imported so never installed, carrying a
typo'd parameter `y_sacle` no caller has ever hit); and **scaffolding for planned
work** (`Q-CO-8`, `Q-CO-5`).

## Decision

**Deleting is the default. Exceptions are allowed; the *inert* state — finished code
that is neither active nor removed — is not.**

A decision procedure, applied per site:

1. **Finished safety or confidence mechanism** → decide **wire it or delete it**.
   Leaving it in place is not an available answer.
2. **Scaffolding for planned work with a live ticket** → keep, but behind an
   explicit `# UNREACHABLE(gh-N)` marker **plus a test asserting it stays
   unreachable**, so it cannot silently half-activate.
3. **Anything else** → **delete**, and record it in the spec as removed.

**The core argument.** "Inert" is the single state in which every cost is paid —
reading, maintenance, review, appearing in every search result — for zero benefit,
**and** in which a protection appears to exist that does not. That second half is
decisive for the switched-off mechanisms: an unwired `validate_geometry` reads like
OpenVSP imports are being sanity-checked when they are not, and a reader who finds
it stops looking for the check that is missing. `Q-CT-3` is the same shape in the
other direction — a dead second ASB entry point carrying the "first wing is the main
wing" assumption that made every coefficient ≈8× wrong (gh-788), fixed in the live
path and not in the copy: *"a latent 8× error waiting for its first caller."*

Rule 2's test requirement is what makes the exception safe: scaffolding kept without
it drifts into rule 1's category the moment someone adds a partial call site.

## Consequences

**Verdicts the policy produced immediately**, on questions open for weeks:

- **`Q-CG-4` — delete, and the whole wing-tessellation subsystem with it.** The
  premise collapsed under investigation: the single-wing 3D preview path is legacy
  in its entirety, superseded by the Plotly outline preview and by shapes delivered
  during construction-plan execution. `useTessellation.ts`, `usePreviewState.ts` and
  `ViewerPanel.tsx` have **no consumers**. Removing it rendered `Q-CG-5`, `Q-FW-5`,
  the `"manual"` geometry-hash placeholder, the tessellation cache race and `Q-CG-3`
  (`bb`) moot at once.
- **`Q-VI-1` — wire it, both halves.** The gh-644 `SS_CONTROL` post-pass was dead
  twice over: `register()` had one caller (a test) and was absent from
  `_ensure_handlers_loaded`, *and* the write path has **no `trailing_edge_device`
  field at all** under its `extra="forbid"` parent, so fixing only the registration
  would change nothing observable.
- **`Q-CG-1` — fix 3MF properly, delete AMF.** AMF has no mapping entry so every
  request 422s; never implemented, superseded by 3MF — deleted under rule 3. 3MF is
  kept and fixed (it carries units, colours and metadata, unlike STL): both defects
  together, plus the test at `test_cad_service_extended.py:130` that asserts the
  wrong string and would keep the suite green through a partial fix.
- **`Q-AA-2` — drop the dead lookup, promote the numbers.**
  `stability_service._get_margin_bounds` queries assumptions `seed_defaults` never
  creates, so the 5 % / 25 % CG bounds are hard-coded **while appearing
  configurable**. Rule 3.

**Cost.**

- **Deletion is irreversible in review terms**, and three of the thirty items are
  genuinely finished work someone paid for — `Q-CG-4` discards ~400 lines of working
  frontend hooks plus a backend service, a cache service, a table and its migration.
- Rule 2 costs a **test per exception** that asserts nothing about behaviour, only
  about reachability.
- The policy forces a decision when the information to decide well may not exist.
  `Q-VI-2` still has **no verdict**: the three finished mechanisms *"still need an
  individual wire-or-delete verdict; this policy only forbids the third answer."*
- The policy is about *reachability*, not quality. `cad_designer/` is inside the
  [ADR 0002](0002-cad-designer-is-frozen-new-creators-only.md) freeze, so removals
  there are **stated in the spec** rather than executed.

**Rejected:** keeping everything (not free where the code is a *safety* mechanism,
because its presence suppresses the search for the check that is missing); a feature
flag (the inert state with extra configuration); deciding each site on its own merits
(the status quo — without a default, "leave it" wins every individual argument and
loses the aggregate).

## Related

- [ADR 0002](0002-cad-designer-is-frozen-new-creators-only.md) — the freeze that
  makes `cad_designer/` removals spec-only.
- [ADR 0018](0018-openvsp-import-scope-is-rc-scaling-inspiration.md) — the scope
  under which `Q-VI-1`'s `SS_CONTROL` wiring is in, and role inference stays out.
- [ADR 0022](0022-one-authority-per-user-facing-quantity.md) — `Q-CT-3` is resolved
  by both policies at once: dead *and* a second producer.
- `P-DEAD-0` in [`../questions.md`](../questions.md), and the **30** questions it
  applies to: `Q-CC-14` · `Q-CC-16` · `Q-AC-1` · `Q-AC-9` · `Q-CT-1` · `Q-CT-3` ·
  `Q-CT-5` · `Q-CG-1` · `Q-CG-4` · `Q-CP-2` · `Q-FD-8` · `Q-VI-1` · `Q-VI-2` ·
  `Q-AV-3` · `Q-AV-8` · `Q-AA-2` · `Q-AA-8` · `Q-MS-13` · `Q-MB-2` · `Q-MB-3` ·
  `Q-MB-10` · `Q-VS-3` · `Q-CO-1` · `Q-CO-5` · `Q-CO-6` · `Q-CO-8` · `Q-CO-10` ·
  `Q-MC-7` · `Q-PT-12` · `Q-FW-8`.
