---
canon: static-thrust-to-weight
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: static-thrust-to-weight
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
tex: \frac{T_0}{W} = \frac{T(V = 0)}{W}
---

# Static thrust-to-weight ratio

**Canonical form**

```
T_0/W = T / W
```

**Produces** [[static-thrust-to-weight]]  ·  **from** [[thrust-at-airspeed]] · [[weight]]

**Kind: a law.** `T` is the thrust at airspeed bound at `V = 0`: the computed static thrust — the motor-propeller balance at `V = 0` on the
measured propeller table — over the weight. A common RC figure: above 1 the model can climb
vertically and hang on the propeller (BRYAN, route A power-limited: 2.0).

**Replaces** (2026-10-02, maintainer) `thrust-to-weight` with `T_mean = f_T · T_static`:
a blanket factor without source on a nameplate thrust that names neither voltage nor
propeller (`mean-thrust-derate`, `mean-thrust`, `static-thrust` deleted). §3.9 had already
stated *"we need no factor for this"*.

**Not the matching-chart ordinate.** For propeller aircraft Sadraey (§4.3.3.2, §4.3.5.2) and RC
practice size on power loading `W/P`, not `T/W` — that belongs to the design direction (O12).

**Source.** 🟢 Definitional (Scholz §5.2 `T_TO/(m·g)`; Sadraey Eq. 4.47).
