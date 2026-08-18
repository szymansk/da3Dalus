---
name: min-spar-spacing
kind: constant
unit: dimensionless (fraction of chord)
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Minimum front–rear spar spacing fraction

**Definition.** Floor on the front–rear chordwise spacing used as the torsion couple's lever arm, so a degenerate layout (front ≈ rear) cannot produce an infinite rear reaction.

**Value.** `0.05`

**Formula — as the code writes it.**

```
_MIN_SPAR_SPACING = 0.05
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_plan_service.py:47` — `_MIN_SPAR_SPACING`

**Consumed by.**

- in this graph: [[spar-spacing-fraction|Front–rear spar chordwise spacing]]
- outside it: `app/services/spar_plan_service.py:413`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (no source read prescribes a minimum front-rear spar spacing; it is a divide-by-zero guard, and ADR 0020 would require a DesignWarning when it fires)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Undeclared clamp (ADR 0020): when the requested layout is degenerate the spacing is silently floored and the rear spar is sized on a lever arm the user did not ask for. No DesignWarning is emitted and the response carries no marker.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `#: Smallest front–rear spacing fraction we will divide by, so a degenerate layout (front≈rear) cannot produce an infinite torsion reaction.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
