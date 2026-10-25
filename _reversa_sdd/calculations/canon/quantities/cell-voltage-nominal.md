---
canon: cell-voltage-nominal
kind: quantity
symbol: U_cell
unit: V
role: input
status: draft
tags:
  - canon/quantity
  - module/construction
  - role/input
type: scalar
positive: true
---

# Nominal cell voltage · `U_cell`

Nominal voltage of one battery cell, the factor between the cell count of the pack and the pack voltage [[battery-voltage]] (`U_bat = cells · U_cell`) and, through it, the pack energy [[battery-capacity]]. An input with a default (`defaults.yaml`, 3.7 V, the usual LiPo nominal value): a LiHV pack is 3.8 V per cell, other chemistries differ, so the caller overrides it where the pack is known. Taking the default is declared (ADR 0020). It is a mid-discharge value, not a measured one; sag under load is not modelled.

**Unit.** `V`

**Used by.** [[airplane-components]]
