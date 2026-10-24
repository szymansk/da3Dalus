---
canon: dynamic-viscosity
kind: quantity
symbol: mu
unit: Pa*s
role: derived
status: draft
tags:
  - canon/quantity
  - stage/references
  - module/atmosphere
  - group/air-state
  - role/derived
type: scalar
---

# Dynamic viscosity of the air · `mu`

Dynamic viscosity at the flight altitude, from the ISA temperature by Sutherland's law (1.7894e-5 Pa·s
at sea level). With [[air-density]] and the speed it forms the Reynolds number `Re = ρ·V·c/μ`.

**Unit.** `Pa*s`

**Produced by.** [[air-density-isa]]

**Used by.** [[aerobuildup-evaluation]] · [[mass-envelope]] · [[minimum-drag-speed-from-polar]] · [[stall-speed]]
