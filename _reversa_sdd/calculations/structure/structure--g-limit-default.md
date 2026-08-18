---
name: structure--g-limit-default
kind: constant
unit: g
cluster: structure
user_visible: true
source_status: PARTIAL
node_class: unclassified-constant
tags:
  - cluster/structure
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Default manoeuvre limit load factor

**Definition.** Load factor substituted when no g_limit design assumption exists for the aeroplane. A warning is logged and (sizing path only) g_limit_fallback=True is returned.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `3.0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_plan_service.py:36` — `_G_LIMIT_DEFAULT`

**Consumed by.**

- in this graph: `Effective manoeuvre load factor` · `Limit load factor (plan path)` · `Manoeuvre limit load factor`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_plan_service.py:356` · `app/services/spar_plan_service.py:358` · `app/tests/test_spar_plan_endpoint.py:414`

**Source.** 🟡 PARTIAL

> Kirch, "Hauptholm", Flugmodellbau Kirch, https://www.flugmodellbau-kirch.de/Hauptholm.htm — tabulated design load factors: normal thermal soarers (Normal-Thermiksegler) 3 G; motorgliders 2.5 G; competition F3J models exceed 65 G (explicitly noted as unsuitable for wood structures)
>
> — via `direct verification of the kirch source named in the code + rc-aircraft-designer (Lennon Ch. 21) + aircraft-design-scholz (Sadraey Table 10.9)`

**The source states it as.**

```
Normal thermal soarers: 3 G (3× aircraft weight).
```

**⚠️ Divergence from the source.** The value 3.0 IS attributable — to the source the module docstring already names — but ONLY for one mission (thermal soarer). The code uses it as the UNIVERSAL default for every aircraft in three separate places (app/services/spar_plan_service.py:36, app/services/analysis_service.py:2099, app/schemas/design_assumption.py:78) plus a fourth silent function default (cad_designer/airplane/geometry/spar_solver.py:724). The same page's own range spans 2.5 G to over 65 G, so the source itself refutes treating 3 G as a general default. It also sits BELOW every mission band in the project's settled record (BR-W16: trainer 4-6 at the lowest) and far below Lennon Ch. 21's 11.8 G worked example. Recommend citing kirch and restricting 3.0 to the thermal-soarer mission.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** THREE independent producers of the same number: app/services/spar_plan_service.py:36, app/services/analysis_service.py:2099, and the assumption registry default app/schemas/design_assumption.py:78 ("g_limit": 3.0). A fourth default, spar_solver.build_stations_from_geometry(g_limit: float = 3.0) at cad_designer/airplane/geometry/spar_solver.py:724, would silently apply if a caller ever omitted the argument. Magic number: no source cited.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `#: Default manoeuvre load factor when no design assumption is set (mirrors analysis_service._G_LIMIT_DEFAULT).`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
