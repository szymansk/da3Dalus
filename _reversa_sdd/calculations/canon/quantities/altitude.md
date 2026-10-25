---
canon: altitude
kind: quantity
symbol: h
unit: m
role: input
tags:
  - canon/quantity
  - module/atmosphere
  - role/input
type: scalar
data:
  - default:altitude
  - app:OperatingPointSchema.altitude
---

# Altitude · `h`

Geometric altitude **above mean sea level** at which the atmosphere is evaluated; used only by the atmosphere ([[air-density-isa]]). The default is 0 m, the ISA reference (`defaults.yaml`, basis `start`, maintainer 2026-10-25); the designer overrides it, e.g. for a field at 500 m. Taking the default is declared (ADR 0020).

**Unit.** `m`

**Used by.** [[air-density-isa]]
