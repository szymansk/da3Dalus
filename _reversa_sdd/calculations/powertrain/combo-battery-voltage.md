---
name: combo-battery-voltage
symbol: voltage
kind: quantity
unit: V
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: WRONG_LINE
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/wrong-line
  - flag/anomaly
  - flag/divergence
---

# Resolved battery voltage (sizing)

**Definition.** Pack nominal voltage resolved from the catalog by a four-step fallback chain: voltage_v, then voltage, then nominal_voltage, then cells x 3.7, then a 3S default of 11.1 V.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
voltage = battery_specs.get("voltage_v")
if voltage is None: voltage = battery_specs.get("voltage")
if voltage is None: voltage = battery_specs.get("nominal_voltage")
if voltage is None and cells: voltage = cells * 3.7
if voltage is None: voltage = 11.1
```

**Inputs.**

- [[volts-per-cell-sizing|Volts per cell (sizing)]]
- [[default-pack-voltage-11v1|Default pack voltage]]  — *⤵ fallback*

**Produced by.** `app/services/powertrain_sizing_service.py:220` — `_evaluate_motor_battery_combo`

🟠 **Corrected by the audit** — the extraction claimed `WRONG_LINE`. Original line was `228`. Voltage resolution chain begins at line 220 (voltage_v lookup), not line 228 (final fallback). Claim formula correctly shows full chain but producer_line points to only the last branch.

**Consumed by.**

- in this graph: `Cruise current draw`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:251`

**Source.** 🟢 SOURCED

> RC-Network Wiki, 'Nennspannung': LiIo/LiPo rated voltage 3.7 V per cell; 'a 3-cell LiPo pack is rated at 3 x 3.7 = 11.1 V'.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
V_pack = S x 3.7 V ;  3S = 11.1 V
```

**⚠️ Divergence from the source.** The cells x 3.7 tier matches the source exactly. The final 11.1 V constant is the source's own 3S worked example used as an unconditional fallback for a pack of unknown cell count, which the source does not support.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The final 11.1 V default is an undeclared fallback: a battery with no voltage data at all is silently treated as 3S with no warning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# The battery component_type schema stores nominal voltage as voltage_v (gh-992); fall back to legacy keys, then derive from cell count (3.7 V/cell nominal), then a 3S default — so a schema-valid battery isn't mis-read as 11.1 V.`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
