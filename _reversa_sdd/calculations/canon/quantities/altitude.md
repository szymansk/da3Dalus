---
canon: altitude
kind: quantity
symbol: h
unit: m
role: input
status: draft
tags:
  - canon/quantity
  - module/atmosphere
  - role/input
type: scalar
---

# Altitude · `h`

Geometric altitude at which the atmosphere is evaluated; the default is 0 m, the ISA sea-level reference (`defaults.yaml`, basis `standard`); the caller overrides it for a field above sea level. Taking the default is declared (ADR 0020).

**Unit.** `m`

**Used by.** [[air-density-isa]] · [[glide-distance-from-ratio]]
