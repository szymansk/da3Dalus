---
canon: polar-stall
kind: quantity
symbol: polar_S
unit: 1
role: derived
status: draft
tags:
  - canon/quantity
  - role/derived
type: polar
---

# Polar at the stall condition · `polar_S`

The sampled whole-aircraft polar — α, `C_L`, `C_D`, `C_m`, of equal length; the solver's drag, not the
parabola (ADR 0026) — at the clean stall condition `V_S`, `n = 1`: the α sweep [[stall-speed]] runs to
bracket the first `C_L` peak, published (maintainer, 2026-10-14, D4). Its range runs far enough past the
peak for [[stall-onset-detection]].

**Unit.** `1` for `C_L`, `C_D`, `C_m`; α in `deg` (the unit of a `polar`, README)

**Produced by.** [[stall-speed]]

**Used by.** [[stall-onset-detection]]
