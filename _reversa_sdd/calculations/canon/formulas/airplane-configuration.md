---
canon: airplane-configuration
entry: formula
kind: procedure
tool: GEO
shape: law
status: draft
output: airplane-takeoff, airplane-landing
source_status: NO_SOURCE_FOUND
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/no-source-found
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
inputs: {airplane: airplane, flap_deflection: null}
outputs: {airplane_cfg: null}
applications:
  # ESCALATED: flap_deflection — which flap angle defines the take-off and the landing
  # configuration is an open domain question; no quantity or sourced constant holds it.
  - id: takeoff
    produce: {airplane_cfg: airplane-takeoff}
  - id: landing
    produce: {airplane_cfg: airplane-landing}
---

# The airplane in its take-off or landing configuration

**Canonical form**

```
airplane_cfg := airplane with its flaps at delta_f,cfg      (cfg = take-off | landing)
```

**Produces** [[airplane-takeoff]] · [[airplane-landing]]  ·  **from** [[airplane]]

**Kind: a procedure — an evaluation of the model.** The same airplane with its flaps set for the
configuration: the flap is in the geometry, not a factor on `C_L,max` ([[stall-speed]], 2026-10-02).
The configured airplane is what the take-off and landing applications of [[stall-speed]] bind
(A2: a named condition is a quantity, produced by its own application — #1181, architect
2026-10-14).

**Without flaps there is no configuration — the same aircraft, not a fallback** ([[stall-speed]],
maintainer 2026-10-02): if the geometry has flaps, they are used as constructed for that
configuration; if it has none, the configured airplane is the airplane itself.

**Open.** Which flap deflection defines each configuration is not decided (escalated in the front
matter).

**Source.** 🔴 NO SOURCE FOUND — a construction step, adopted on the maintainer's statement in
[[stall-speed]] (2026-10-02).
