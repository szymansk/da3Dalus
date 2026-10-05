---
canon: vertical-tail-volume
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: vertical-tail-volume
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/law
  - status/draft
---

# Vertical tail volume

**Canonical form**

```
S_V, l_V, S, b := geometry(airplane)   # fin area (V-tail: S_Vtail*sin^2(nu)), tail arm, wing area, span
V_V = S_V * l_V / (S * b)
```

`S_V` is the fin area, for a V-tail its fin share `S_Vtail·sin²ν` (ν = panel angle to the horizontal);
`l_V` runs from the wing's to the fin's quarter-chord MAC.

**Produces** [[vertical-tail-volume]]  ·  **from** [[airplane]]

**Kind: a law.** A geometric ratio, deterministic and independent of any solver. It is the robust anchor
next to the AVL derivatives (K27): RC practice and preliminary design size the fin with it, not with
`C_nβ` (Sadraey §6.7.1; Drela, desrules Eq. 7).

**Precondition.** The aircraft has a fin or a V-tail behind the wing. For a tailless aircraft (winglets,
centre fin on the wing) the lever is not a tail arm and the value is not computed — not computed
differently. No sourced rule for flying-wing fins exists (research 2026-10-04).

**Values, not verdicts (A10).** The bands — RC/UAV 0.02–0.05, gliders ≈ 0.03 (Sadraey Tab. 6.4; Drela)
— belong to the evaluation.

**Dimensional check.** 🟢 balances by hand — m²·m / (m²·m); the checker sees a geometry extraction (procedural).

**Source.** 🟢 SOURCED — Sadraey Eq. 6.74; V-tail projection sin²ν: McCombs, *Model Aviation* 7/1996;
Drela's V-tail rule (BAENDER §3b).

**Validity at 0.5–15 kg.** Exact as geometry; the bands are RC values.
