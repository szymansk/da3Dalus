---
name: cl-max-landing
symbol: CL_max,landing
kind: quantity
unit: – (dimensionless)
cluster: stability
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Landing CL_max

**Definition.** Maximum lift coefficient in the landing configuration; the denominator of the trim inversion.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cl_max_landing = cl_max_clean + (_ROSKAM_FLAP_CL_BONUS if has_flap else 0.0)
```

**Inputs.**

- [[cl-max-clean-fallback|Clean CL_max fallback]]  — *⤵ fallback*
- [[roskam-flap-cl-bonus|Flap CL_max increment]]  — *⊣ limit*
- [[cl-max-landing-flap|Swept flapped CL_max]]  — *⊣ limit*

**Produced by.** `app/services/elevator_authority_service.py:361` — `_build_stub_result`

**Consumed by.**

- in this graph: `Forward CG limit (trim inversion)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/elevator_authority_service.py:374,654,671,790,832,1025,1131,1167` · `app/schemas/forward_cg.py:72` · `app/api/v2/endpoints/aeroplane/forward_cg.py:99`

**Source.** 🟢 SOURCED

> Scholz HAW Hamburg, 08_HighLift §8.2 (Integration of Flap and Slat Contributions): C_L,max = C_L,max,clean + ΔC_L,max,f + ΔC_L,max,s. Reference values by type: Scholz 05_PreliminarySizing §5.1 Table 5.1.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_L,max = C_L,max,clean + ΔC_L,max,f + ΔC_L,max,s   (Scholz 08_HighLift §8.2)
```

**⚠️ Divergence from the source.** The additive structure matches. The increment does not: the source's ΔC_L,max,f is computed per aircraft (k₁·k₂·k₃·base · flapped-area ratio · sweep factor), while the code substitutes a flat +0.5 (see roskam-flap-cl-bonus). The source also carries a slat term ΔC_L,max,s the code has no path for. Four independent producers of this same user-visible number exist in the app (the +0.5 formula at :361/:671/:1025, the swept flap result at :654, the clean pass-through at :675, and assumption_compute_service:774's polar_by_config['landing']['cl_max']) — ADR 0022.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Table 5.1 and the DATCOM integration are transport/GA-category (CS-25). Applying them at 0.5–15 kg is unvalidated (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Three producers of the same user-visible number: the Roskam-bonus formula (lines 361, 671, 1025), the swept flap result (line 654 via cl_max_landing_flap), and the clean pass-through (line 675). assumption_compute_service:774 independently produces polar_by_config['landing']['cl_max'] — a fourth, unrelated landing CL_max in the same app (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `CL_max_landing (Roskam §4.7):
  With flap: CL_max_landing = CL_max_clean + 0.5
  Without flap: CL_max_landing = CL_max_clean`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
