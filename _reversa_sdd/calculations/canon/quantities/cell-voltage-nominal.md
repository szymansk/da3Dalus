---
canon: cell-voltage-nominal
kind: quantity
symbol: U_cell
unit: V
role: input
tags:
  - canon/quantity
  - module/construction
  - role/input
type: scalar
data: default:cell-voltage-nominal

positive: true
---

# Nominal cell voltage · `U_cell`

Nominal voltage of one battery cell, the factor between the cell count of the pack and the pack voltage [[battery-voltage]] (`U_bat = cells · U_cell`) and, through it, the pack energy [[battery-capacity]]. An input with a sourced default (`defaults.yaml`): 3.7 V, the **LiPo** value. The sourced nominal values per cell by chemistry (SkyRC Blog, 2024-12-26) are LiPo 3.7 V, LiHV 3.8 V, LiFe 3.2 V, Li-Ion 3.6 V, NiMH 1.2 V; the caller overrides the default where the pack is another chemistry. A per-chemistry default needs a battery chemistry in the component data (the catalogue has none) and a component-data `when` predicate: #1236 and #1245. Taking the default is declared (ADR 0020). It is a mid-discharge value, not a measured one; sag under load is not modelled.

**Unit.** `V`

**Used by.** [[airplane-components]]
