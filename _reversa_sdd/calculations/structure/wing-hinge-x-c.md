---
name: wing-hinge-x-c
symbol: x/c_hinge
kind: quantity
unit: dimensionless (x/c)
cluster: structure
user_visible: false
source_status: SOURCED
---

# Most-forward control-surface hinge

**Definition.** The most forward control-surface hinge line on the wing, as a chord fraction. Binding constraint for the computed rear spar, which must clear EVERY control surface.

**Formula — as the code writes it.**

```
hinges = [
    ted.rel_chord_root
    for xsec in getattr(wing, "x_secs", None) or []
    if (detail := getattr(xsec, "detail", None)) is not None
    if (ted := getattr(detail, "trailing_edge_device", None)) is not None
    if getattr(ted, "rel_chord_root", None) is not None
]
return min(hinges) if hinges else None
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_plan_service.py:294` — `_wing_hinge_x_c`

**Consumed by.**

- in this graph: [[rear-spar-x-c-clamped|Clamped rear-spar chord location]]
- outside it: `app/services/spar_plan_service.py:588` · `cad_designer/airplane/geometry/spar_solver.py:742`

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §12.4.3 "Aileron Design Constraints", constraint 4 "Wing Rear Spar"; Scholz, Flugzeugentwurf, 07_WingDesign §7.4, p. 7-42; Lennon, The Basics of R/C Model Aircraft Design (1996), Ch. 13
>
> — via `aircraft-design-scholz (lead) + rc-aircraft-designer`

**The source states it as.**

```
Sadraey §12.4.3(4), verbatim in substance: "The aileron needs a hinge line. Using the wing rear spar as the most forward limit gives a lighter, less complex structure. This may limit aileron chord but improves wing structural integrity. Aileron and flap should ideally have the same chord so the rear spar holds both." Scholz §7.4: "the hinge line of the spoilers is located directly behind the rear spar. Space has to be left between the rear spar and the hinge line to accommodate the drive mechanism of the ailerons." Lennon Ch. 13: "An aft spar carries flap or aileron hinge loads".
```

**⚠️ Divergence from the source.** All three sources agree the rear spar constrains the hinge line, and Sadraey states the relation in the same direction the code enforces it. The code's decision to apply the hinge constraint to the rear spar only (app/services/spar_plan_service.py:580-582) and pass none to the front spar matches Scholz §7.4 in the trailing-edge case, but no source read covers a leading-edge device constraining the front spar — that case is simply unaddressed.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey §12.4.3 and Scholz §7.4 both reason from transport/GA hardware (spoiler drive mechanisms, flap-aileron chord matching). At RC/UAV scale the hinge is usually a film or pinned hinge with no drive mechanism to clear, so the required margin is a different physical quantity. The CONSTRAINT transfers; the sizing of the gap does not.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Deliberately applied to the rear spar only (spar_plan_service.py:580-582); the front spar is passed no hinge, so a wing with a leading-edge device would not constrain the front spar. That is documented as intentional, not a defect.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** ```rel_chord_root`` is the hinge x/c: it is populated from AeroSandbox's ``hinge_point`` when a control surface is projected onto a cross-section (``app/models/aeroplanemodel.py:320-324``).`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
