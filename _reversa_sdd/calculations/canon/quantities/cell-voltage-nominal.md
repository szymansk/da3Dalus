---
canon: cell-voltage-nominal
kind: quantity
symbol: U_cell
unit: V
role: derived
tags:
  - canon/quantity
  - stage/references
  - module/construction
  - point/none
  - group/powertrain-battery
  - role/derived
type: scalar
data:
  - component:battery.cell_voltage_v
  - component:battery.chemistry
  - default:cell-voltage-nominal
---

# Nominal cell voltage · `U_cell`

Nominal voltage of one cell of the battery fitted to the airplane: the factor between the cell count and the pack voltage [[battery-voltage]] (`U_bat = cells · U_cell`) and, through it, the pack energy [[battery-capacity]]. It is a property of the battery, read by [[airplane-components]] from the catalogue field `battery.cell_voltage_v` (maintainer, 2026-10-25, #1245); the catalogue states it per battery from the datasheet, and `voltage_v = cells · cell_voltage_v` holds for every entry (a finding if not — one authority, ADR 0022).

**Fallback chain** (each step declared with a `practice` warning, ADR 0020): a battery without `cell_voltage_v` takes the value of its `chemistry` (closed enumeration; SkyRC Blog, 2024-12-26): `lipo` 3.7 V, `lihv` 3.8 V, `life` 3.2 V, `li_ion` 3.6 V, `nimh` 1.2 V; a battery with neither takes the default of `defaults.yaml`, 3.7 V (LiPo), a starting value the designer replaces once a battery is chosen. It is a mid-discharge value, not a measured one; sag under load is not modelled.

**Unit.** `V`

**Produced by.** [[airplane-components]]
