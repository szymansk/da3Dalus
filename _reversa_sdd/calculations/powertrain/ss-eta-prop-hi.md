---
name: ss-eta-prop-hi
symbol: eta_prop_hi
kind: parameter
unit: dimensionless (0..1)
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Propeller efficiency band upper bound

**Definition.** Optimistic end of the assumed propeller efficiency band.

**Value.** `0.78`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/powertrain_solution_space.py:35` — `SolutionSpaceAssumptions.eta_prop_hi`

**Consumed by.**

- in this graph: [[ss-eta-mid|Mid-band propeller efficiency]] · [[ss-p-cruise-hi-e|Electrical cruise power at high prop efficiency]] · [[ss-p-elec|Electrical power required]] · [[ss-p-top-hi-e|Electrical peak power at high prop efficiency]]
- outside it: `app/services/powertrain_solution_space_service.py:357` · `app/services/powertrain_solution_space_service.py:368` · `app/services/powertrain_solution_space_service.py:373`

**Source.** 🟢 SOURCED

> Deters, Ananda & Selig (2014), §VI: 'the maximum achievable efficiency eta_max remains constrained to roughly 60-70% for propellers in the low-Re regime typical of UAVs and MAVs ... this ceiling is not easily circumvented by geometry optimization alone.' Contrast Sadraey (2013) §8.7/§8.8.1: eta_P 0.75-0.85 at cruise with optimum blade pitch (full-scale).
>
> — via `rc-aircraft-designer / aircraft-design-scholz`

**The source states it as.**

```
eta_max ~ 0.60-0.70 at low Re (Deters §VI);  eta_P = 0.75-0.85 full-scale (Sadraey §8.7)
```

**⚠️ Divergence from the source.** 0.78 sits ABOVE the 0.60-0.70 ceiling that Deters/Ananda/Selig measure for exactly this propeller class, and inside Sadraey's full-scale 0.75-0.85 band. The value therefore looks like a transport/full-scale figure imported into an RC-scale band. Deters' direct comparison is the counterexample: the 10-ft NR640 exceeds 80% while its geometrically equivalent 9-inch model stays below 65%.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** ADR 0023 finding. 0.78 is not attributable at 0.5-15 kg RC/UAV scale; the only sources that reach it (Sadraey §8.7, eta_P 0.75-0.85) are full-scale GA/transport propellers. The RC-scale measurements cap eta_max at ~0.70, so the optimistic end of the efficiency band understates required power, capacity and current across every consumer.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic number with no source. No validation enforces eta_prop_hi > eta_prop_lo — the schema constrains each to [0.01, 0.99] independently, so an inverted band is accepted and silently inverts the lo/hi columns.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
