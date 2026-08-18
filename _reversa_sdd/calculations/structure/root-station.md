---
name: root-station
kind: quantity
unit: -
cluster: structure
user_visible: true
source_status: SOURCED
---

# Root sizing station

**Definition.** The innermost sized station — the headline (worst-case) result for a typical wing. Taken as the LAST element because the station list is ordered tip-to-root.

**Formula — as the code writes it.**

```
root_station = sized_stations[-1] if sized_stations else _zero_station()
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_sizing.py:352` — `compute_spar_sizing`

**Consumed by.**

- outside it: `app/services/spar_sizing.py:381` · `app/schemas/spar_sizing.py:131` · `frontend/lib/sparSizingHelpers.ts:89`

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §7.9.3 — "the wing lift force generates a large bending moment at the wing/fuselage attachment"; §10.4.1 Table 10.8 note — "as the distance between the fuel tank/engine and the wing root increases, the wing will be heavier in order to handle the larger root bending moment"; Scholz, Flugzeugentwurf, 07_WingDesign §7.4 / [[wing-box-spars]] — structural depth "increases toward the root (where bending moments are largest)"
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
The root is the governing (maximum-bending-moment) station for a cantilever wing.
```

**⚠️ Divergence from the source.** The engineering claim is well sourced. The IMPLEMENTATION contract is not: taking `sized_stations[-1]` depends entirely on the caller supplying stations tip-to-root, which no source addresses and nothing in the code validates.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Silent ordering contract: correctness depends entirely on the caller supplying stations tip-to-root. The only production caller (analysis_service._surface_to_stations:2201) passes the loads entries through in whatever order the loads result has; nothing validates the ordering.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Root station = innermost (last in outboard-first list)`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
