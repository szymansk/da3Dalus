---
canon: static-margin-probe
entry: formula
kind: procedure
tool: AB
shape: law
status: draft
output: pitching-moment-slope, static-margin-probe
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
---

# Static margin from the moment slope — the Probe

**Canonical form**

```
solve for alpha at V_md:   L = m * g
C_m_alpha, C_L_alpha := AeroBuildup(airplane, x_ref = x_CG, V_md, alpha).run_with_stability_derivatives()
SM_probe = - C_m_alpha / C_L_alpha
```

**Produces** [[pitching-moment-slope]] · [[static-margin-probe]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[minimum-drag-speed]] · [[centre-of-gravity]]

**Kind: a procedure — the Probe of [[static-margin]].** With the moment reference at the
CG, `−C_mα/C_Lα` is the static margin by a second path. Two paths to one quantity are a
**test**, not a second truth (A7): a deviation beyond tolerance is reported, never averaged.

Unlike `x_NP`, `C_mα` **does** depend on the reference: its sign flips exactly at
`x_ref = x_NP` (§2.3). That is why the Probe — and only the Probe — needs the CG.

**Source.** 🟢 `SM = −C_mα/C_Lα` (Anderson §4.9 / standard).
