---
name: fe_cl_min_factor
symbol: -0.8
kind: constant
unit: -
cluster: perf-envelope
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/perf-envelope
  - class/unclassified-constant
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# Negative CL_max ratio

**Definition.** Ratio of inverted to upright maximum lift coefficient.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `-0.8`

**Formula — as the code writes it.**

```
cl_min = -0.8 * cl_max
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:316` — `compute_vn_curve`

**Consumed by.**

- in this graph: `Inverted maximum lift coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🔴 NO SOURCE FOUND

> No source for -0.8 in any consulted vault.
>
> — via `rc, aero`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Worse than uncited — it is wrong for the case that matters. Lennon, Basics of R/C Model Aircraft Design (1996), airfoil chapter: aerobatic RC models use SYMMETRICAL sections (NACA 0012 CL_max ~ 1.05, NACA 64-012 CL_max ~ 0.9 at Rn 700k) precisely so that inverted and upright performance are identical — for those the true ratio is -1.0, not -0.8. The negative branch of the V-n diagram only gets exercised by aerobatic models, so the constant is 20% conservative exactly where it is used and unvalidated everywhere else. A cambered trainer would justify a ratio below -0.8; the code applies one number to both.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number, no comment and no citation. Governs the whole negative stall branch of the diagram.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
