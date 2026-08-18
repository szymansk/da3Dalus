---
name: vlm-spanwise-resolution-fixed
symbol: spanwise_resolution
kind: constant
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: PARTIAL
---

# VLM spanwise_resolution literal

**Definition.** VLM spanwise resolution is pinned to 1 because density is already set by the remesh.

**Value.** `1`

**Formula — as the code writes it.**

```
spanwise_resolution=1,  # gh-855: density set by the remesh, not here
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:208` — `compute_vlm_strip_forces`

**Consumed by.**

- in this graph: [[vlm-wing-strip-counts|Expected strips per wing]]
- outside it: `app/services/vlm_strip_forces.py:_wing_strip_counts (called with 1 at line 234)`

**Source.** 🟡 PARTIAL

> AeroSandbox docs_aero_3d.md (spanwise_resolution = panels per wing SECTION, not per wing)
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** Setting it to 1 is correct given the pre-remesh, since ASB applies the resolution per xsec interval. Bookkeeping, not a physical model.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:208`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
