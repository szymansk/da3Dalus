---
name: ss-cell-counts
symbol: cell_counts
kind: parameter
unit: cells (S)
cluster: powertrain
user_visible: true
source_status: PARTIAL
---

# Evaluated cell counts

**Definition.** The LiPo series cell counts for which a solution row is produced.

**Value.** `[2, 3, 4, 6]`

**Formula — as the code writes it.**

```
for s in assumptions.cell_counts:
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/powertrain_solution_space.py:25` — `SolutionSpaceAssumptions.cell_counts`

**Consumed by.**

- in this graph: [[ss-v-nom|Pack nominal voltage (solution space)]] · [[ss-v-sag|Pack voltage under load]]
- outside it: `app/services/powertrain_solution_space_service.py:383` · `frontend/hooks/usePowertrainSolutionSpace.ts:116`

**Source.** 🟡 PARTIAL

> Roxxy Motoren-Fibel, Ch. 1, pp. 15-16 discusses cell count as a first-class design lever ('Battery cell count (3S, 4S, 5S, etc.) directly sets the no-load RPM target') and works the C3530-06 on 3S vs C3530-09 on 4S trade. RC-Network Wiki 'Nennspannung' gives the S x 3.7 V rating rule.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
V_pack = S x 3.7 V; cell count sets the no-load RPM target
```

**⚠️ Divergence from the source.** The Roxxy source names 3S, 4S and 5S explicitly as the practitioner's options. The code's list [2, 3, 4, 6] skips 5S, which the source treats as a normal choice, and includes 2S and 6S, which it does not enumerate.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Skips 5S with no explanation; no validation that entries are positive or unique.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `field description: "LiPo cell counts to evaluate (e.g. [2, 3, 4, 6])"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
