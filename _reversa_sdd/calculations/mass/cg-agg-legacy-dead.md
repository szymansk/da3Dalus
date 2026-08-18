---
name: cg-agg-legacy-dead
symbol: x_cg,agg,legacy
kind: quantity
unit: m
cluster: mass
user_visible: false
source_status: SOURCED
code_audit: NOT_VERIFIED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/sourced
  - audit/not-verified
  - flag/anomaly
  - flag/divergence
---

# Legacy weight-item CG loader (dead)

**Definition.** Mass-weighted CG_x computed directly from the weight-item table, bypassing loading scenarios.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
items = [{"mass_kg": r.mass_kg, "x_m": r.x_m, "y_m": r.y_m, "z_m": r.z_m} for r in rows]; _, cg_x, _, _ = aggregate_weight_items(items); return cg_x
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/assumption_compute_service.py:1739` — `_load_cg_agg`

⚪ **Not verified.** This node was not covered by the audit pass; treat its line and formula as extracted-but-unchecked.

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.2 Eq. (11.1), X_cg = ΣW_i·x_cg,i / ΣW_i = Σm_i·x_cg,i / Σm_i — the code body is a literal implementation of this equation over a flat item list. Scholz, D., "Flugzeugentwurf" (HAW Hamburg), Design Sequence §2.2 Step 10 sub-step c states the same procedure in words.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
X_cg = ΣW_i·x_cg,i / ΣW_i   (Sadraey Eq. 11.1)
```

**⚠️ Divergence from the source.** The formula is correct and correctly sourced; the code is unreachable (no call site for _load_cg_agg anywhere in app/, cad_designer/, scripts/ or tests) and is duplicated verbatim in loading_scenario_service.py:384-393. Notably this dead path is the only place in the cluster that computes cg_y and cg_z alongside cg_x — i.e. the only implementation of Sadraey Eqs. (11.2)/(11.3) — and it is the one that was retired.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** NO CONSUMER. Repo-wide grep for '_load_cg_agg' returns only the definition at line 1739. Superseded by compute_cg_agg_for_aeroplane (gh-488) whose legacy branch (loading_scenario_service.py:384-393) is a verbatim duplicate of this body. Complete-but-unreachable code (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Return mass-weighted CG x from weight items, or None if no items exist." — app/services/assumption_compute_service.py:1740`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
