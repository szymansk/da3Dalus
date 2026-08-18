---
name: mac-solver-cref
symbol: c_ref
kind: quantity
unit: m
cluster: stability
user_visible: true
source_status: SOURCED
---

# MAC (solver reference chord)

**Definition.** Mean aerodynamic chord taken from the solver's reference block, used to normalise the static margin.

**Formula — as the code writes it.**

```
mac_val = _scalar(result.reference.Cref)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/stability_service.py:327` — `get_stability_summary`

**Consumed by.**

- in this graph: [[cg-range-aft|Aft CG limit from margin bounds]] · [[cg-range-forward|Forward CG limit from margin bounds]] · [[static-margin-fraction|Static margin (fraction of MAC)]]
- outside it: `app/services/stability_service.py:328,333,334,353` · `app/services/copilot_tools.py:447,462`

**Source.** 🟢 SOURCED

> Scholz HAW Hamburg, 07_WingDesign §7.1 — Mean Aerodynamic Chord: c_MAC = (2/S)·∫₀^(b/2) c² dy, and for a simple tapered wing c_MAC = (2/3)·c_r·(1+λ+λ²)/(1+λ). MAC is the reference length for all dimensionless aerodynamic coefficients.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
c_MAC = (2/S)·∫₀^(b/2) c² dy ;  tapered wing: c_MAC = (2/3)·c_r·(1+λ+λ²)/(1+λ)
```

**⚠️ Divergence from the source.** The code does not evaluate this integral; it takes the solver's reference chord. Fine when the solver's Cref is the true MAC of the main wing — but assumption_compute_service:1087 computes mac = main_wing.mean_aerodynamic_chord() independently, so two chords normalise the same SM.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer: assumption_compute_service:1087 computes mac = main_wing.mean_aerodynamic_chord() from the MAIN wing rather than the solver's reference — the two normalise SM against different chords (documented at copilot_tools.py:440-442).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
