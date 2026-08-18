---
name: stock-density-fallback
symbol: ρ
kind: constant
unit: kg/m³
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/structure
  - class/unclassified-constant
  - source/no-source-found
  - flag/anomaly
---

# Stock density fallback

**Definition.** Density assumed for a stock item whose specs omit density_kg_m3, used in the lightest-stock ranking.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1550.0`

**Formula — as the code writes it.**

```
density = float(row.specs.get("density_kg_m3", 1550.0))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_plan_service.py:160` — `snap_piece_to_stock`

**Consumed by.**

- in this graph: `Linear mass of a stock cross-section`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_plan_service.py:161`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer (RC-Network Wiki "CFK" and "Kohlefaser" give carbon density qualitatively only — no kg/m³ value); aircraft-design-scholz (Sadraey Table 10.6 material densities is referenced by Eq. 10.3 but no specific CFRP value was retrievable). 1550 kg/m³ is unattributed anywhere in the code and is applied as a silent ADR 0020 fallback that can win the "lightest stock" ranking on a fabricated number.`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Magic number with no explanation and no source anywhere in the file. Undeclared fallback (ADR 0020): a stock item with missing density is silently ranked as if it were 1550 kg/m³ and can win the 'lightest' selection on a fabricated number, with no warning.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
