---
name: mac
symbol: MAC
kind: quantity
unit: m
cluster: mass
user_visible: true
source_status: SOURCED
code_audit: NOT_VERIFIED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/not-verified
  - flag/divergence
---

# Mean aerodynamic chord (main wing)

**Definition.** Mean aerodynamic chord of the MAIN wing (largest planform area), used as the length scale that converts CG offsets into static margins.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
mac = float(main_wing.mean_aerodynamic_chord())
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/assumption_compute_service.py:1087` — `_stability_run_at_cruise`

⚪ **Not verified.** This node was not covered by the audit pass; treat its line and formula as extracted-but-unchecked.

**Consumed by.**

- in this graph: `Aft CG stability limit` · `Forward CG stability limit (0.30·MAC stub)` · `Design CG_x (aerodynamic CG target)` · `Static margin at aft loading CG (API)` · `Static margin at aft loading CG (cached)` · `Static margin at forward loading CG (API)` · `Static margin at forward loading CG (cached)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/assumption_compute_service.py:108 (cg_x)` · `app/services/assumption_compute_service.py:473` · `app/services/assumption_compute_service.py:706 (ctx['mac_m'])` · `app/services/loading_scenario_service.py:112 / :116 / :259 / :260 / :584 / :593-594` · `app/services/sm_sizing_service.py` · `app/services/tail_sizing_service.py` · `frontend/components/workbench/StabilityChipRow.tsx:27` · `frontend/lib/metricsAdapters.ts:234 / :344`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.4 Eq. (11.11): h = X̄_cg = (x_cg − x_LE,MAC)/C̄, where C̄ is the WING mean aerodynamic chord — the length that non-dimensionalises every longitudinal cg quantity in the chapter, including SM (Eq. 11.18), the cg range (Eq. 11.16) and the horizontal-tail volume coefficient V̄_H = (S_h·l_h)/(S·C̄) (Eq. 11.20). Scholz, D., "Flugzeugentwurf" (HAW Hamburg), Design Sequence §2.2 Step 10 uses the same convention ("CG within acceptable range — typically 20–30% MAC aft of wing leading edge").
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
h = X̄_cg = (x_cg − x_LE,MAC) / C̄   (Sadraey Eq. 11.11), with C̄ = wing MAC
```

**⚠️ Divergence from the source.** The code's documented choice to take the MAIN wing (largest planform area) rather than AeroSandbox's reference chord (assumption_compute_service.py:1073-1074) AGREES with the sources: in Sadraey Eqs. (11.11), (11.18) and (11.20), C̄ and S are unambiguously the WING's MAC and area, not a solver's arbitrary reference. Worth recording as a confirmed-correct decision rather than a divergence. What is missing relative to the source is the datum: Sadraey measures cg from x_LE,MAC (the wing leading edge at MAC), and the code never establishes that x_np and x_cg share that origin — the SM ratio survives any common datum, but the % MAC figures reported to the user do not.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"For MAC and S_ref, takes the **main wing** (largest planform area) rather than ASB's reference." — app/services/assumption_compute_service.py:1073-1074`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
