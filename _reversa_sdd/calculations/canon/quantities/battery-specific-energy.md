---
canon: battery-specific-energy
kind: quantity
symbol: E_star
unit: Wh/kg
role: input
status: draft
tags:
  - canon/quantity
  - module/construction
  - role/input
type: scalar
---

# Specific energy of the battery · `E_star`

A **design assumption** of [[battery-mass-from-capacity]] and of nothing else (maintainer, 2026-10-25, #1235): the energy per mass the designer expects of the battery, with its **basis** stated — cell or pack. It is not read from a component: derived from a real pack it would make the mass plausibility check tautological. The default value is an **open decision** (catalogue packs give 128–159 Wh/kg, the app default is 180 Wh/kg, the canon's cited source gives 152.8 Wh/kg at cell level); until it is decided there is no default and the value is a required input.

**Unit.** `Wh/kg`

**Used by.** [[battery-mass-from-capacity]]
