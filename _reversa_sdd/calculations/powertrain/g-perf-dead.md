---
name: g-perf-dead
symbol: G
kind: constant
unit: m/s^2
cluster: powertrain
user_visible: false
source_status: PARTIAL
---

# Gravitational acceleration (performance module)

**Definition.** Standard gravity declared at the top of the performance module.

**Value.** `9.80665`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:49` — `G`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🟡 PARTIAL

> No expert vault attributes the value. 9.80665 m/s^2 is the standard acceleration of free fall fixed by the 3rd CGPM (1901, Resolution 2); neither Scholz/Sadraey nor Anderson state it to 6 significant figures in the material consulted.
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Not a divergence of form — the constant is never read (dead), so no formula exists to compare.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** DEAD CONSTANT. grep for the symbol across app/ returns only this definition line — nothing in powertrain_performance.py uses G, and no module imports it. ADR 0021 (complete but unreachable) candidate.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# m/s²`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
