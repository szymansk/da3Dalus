---
name: pitching-moment-proxy-ratio
symbol: T/M
kind: parameter
unit: dimensionless
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Pitching-moment proxy ratio

**Definition.** Ratio of section torsion to bending moment assumed when no explicit torsion distribution is given.

**Value.** `0.10`

**Formula — as the code writes it.**

```
pitching_moment_proxy_ratio: float = Field(
    0.10,
    ge=0.0,
    ...
)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/spar_plan.py:154` — `SparPlanRequest.pitching_moment_proxy_ratio`

**Consumed by.**

- in this graph: [[torsion-proxy|Torsion proxy from bending moment]]
- outside it: `app/services/spar_plan_service.py:447` · `app/services/spar_plan_service.py:450`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer. The code's own justification, "T(y)/M(y) ≈ \|Cm\|/\|CL\| · 1 representing the section torsion as a fraction of the bending moment... a typical cambered-airfoil pitching-moment-to-bending ratio", is not attributable to any source read, and is dimensionally incomplete on its own terms: the trailing "· 1" stands in for a length ratio (chord over the spanwise moment arm) that is never computed. Note also this parameter is unreachable from the UI — frontend/hooks/useSparPlan.ts buildPlanBody never sends torsion_moments, so every browser-originated rear spar is sized on this unattributed 0.10.`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Magic number with a rationale but no citation ('a typical cambered-airfoil pitching-moment-to-bending ratio'). The stated derivation 'T(y)/M(y) ≈ \|Cm\|/\|CL\| · 1' is dimensionally hand-waved — the trailing '· 1' stands in for a length ratio that is never computed. Not reachable from the UI (see torsion-proxy).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `gh-1038: Used ONLY when torsion_moments is not supplied. Proxy ratio T(y)/M(y) ≈ \|Cm\|/\|CL\| · 1 representing the section torsion as a fraction of the bending moment. Default 0.10 (a typical cambered-airfoil pitching-moment-to-bending ratio). Replace with a real T(y) from the strip pitching moments when available (follow-up #1002 extension).`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
