# Feature proposal — show the designer what the aircraft will feel like

**Status:** proposal, recorded 2026-08-15 at the maintainer's request. Not a ticket yet.
**Origin:** arose while answering `Q-AV-8` (dynamic-mode scope). It is the answer to a
question the interview did not ask — *how do you communicate a stability result to
someone who does not read stability derivatives?*

## The problem this solves

The expert consultation concluded that at 0.5–15 kg three of five dynamic modes are
non-issues (roll subsidence ×14 margin, dutch roll ×1.4–12, short period above human
pilot bandwidth). **The maintainer, an FPV pilot, disagreed from experience** — dutch
roll is genuinely annoying in flight, and on flying wings it is a permanent,
configuration-induced defect rather than a gust response.

Both were right, and the disagreement was productive:

- The **free-decay** view (one gust, decays — what the ×1.4 margin describes) is not what
  a pilot experiences. In gusty low-altitude air the mode is **continuously re-excited**
  and never settles. Same ζ, but it enters as *sustained amplitude* rather than decay
  time: a lightly damped mode is a narrow-band resonant filter on the turbulence spectrum.
- **Frequency matters as much as damping.** A dutch roll at ω ≈ 5 rad/s sits at the edge
  of human pilot bandwidth (~2–3 rad/s); a flying wing's at ω ≈ 2.4 rad/s sits **inside**
  it. The maintainer's own observation — *"sonst reagiert man mit dem Knüppel gegen und
  verschlimmert die Situation"* — is pilot coupling, and it is a **frequency** problem.
  This is why MIL-F-8785C specifies ζ, ζ·ω and ω separately rather than ζ alone.

A number cannot carry any of that. An animation can.

## Why flying wings are the case that matters

Structural, not incidental:

- **`C_nβ` tiny** — fins sit on the root or as winglets; the moment arm is a chord, not a
  boom.
- **`C_nr` almost absent** — yaw damping is fin force × arm. No arm, no damping. This is
  the root cause.
- **`C_lβ` large anyway** — the sweep needed for longitudinal stability produces
  `C_lβ ∝ −C_L·sin 2Λ` as a side effect. It cannot be removed without abandoning the
  configuration.

Low `C_nβ` lowers **both** frequency and damping, so it makes the mode worse twice over.
This converges with two things already in the record: the aerodynamics authority flagged
`V_v < 0.008` (flying wing with vestigial fins) as the regime where the fuselage `Cnb`
term can flip sign, and the RC literature names the same corner as *"too much dihedral
effect, too little fin → dutch roll"*.

## What is computable today, measured

| parameter | source | available? |
|---|---|---|
| `Cnb`, `Clb` → roll/yaw coupling | AeroBuildup, `stability_service.py:325-326` | ✅ **13 stored results in the live DB** |
| `Cnr`, `Clr` → damping | **not in AeroBuildup** — only `aero_3D/avl.py` | ❌ needs an AVL run |
| `I_zz` → frequency *and* damping | `component_tree.pos_x/y/z` + mass exist | ⚠️ schema yes, **data no** — 12 populated nodes total, best aircraft has 3 |
| roll/yaw ratio and phase, exactly | AVL `MODE` **eigenvector** | ❌ needs `.mass`/`.run` |

Real spread over the maintainer's own aircraft, `|Clb/Cnb|`:

| aircraft | Cnb | Clb | ratio | reading |
|---|---|---|---|---|
| Cessna 172N | 0.0761 | −0.0451 | **0.59** | the calibration anchor — a known-docile aircraft |
| eHawk | 0.0766 | −0.0715 | 0.93 | |
| eHawk (other rev) | 0.0185 | −0.0484 | 2.62 | |
| Schleicher ASK-21 | 0.0203 | −0.0808 | **3.99** | long-span glider, plausible |
| Olek | **−0.0014** | −0.0940 | 66 | **`Cnb` negative — directionally unstable** |
| saal_flug | −0.000048 | −0.0039 | 81 | `Cnb` negative |

The Cessna is the load-bearing row: an aircraft whose handling everyone knows anchors the
scale, so the others can be read against it rather than against an invented threshold.

## Proposed staging

**Stage 1 — today, no new data.** Report `|Clb/Cnb|` as a *dutch-roll coupling*
indicator, with the Cessna anchor shown alongside. Warn when `Cnb ≤ 0` (directional
instability, which two stored designs already exhibit). The animation may be rendered at
this stage **only** with frequency and damping shown as assumed defaults and labelled as
such — an animation reads as authoritative, and inventing two of four parameters silently
is exactly the undeclared substitution **ADR 0020** forbids.

**Stage 2 — with a populated component tree + an AVL run.** ω and ζ become real.
Declare the fraction of total mass actually accounted for by positioned components; below
a threshold, **refuse rather than guess**.

**Stage 3 — AVL `MODE`.** The **eigenvector** *is* the roll/yaw amplitude ratio and
phase — the two parameters currently set by hand. At this stage the animation contains no
assumption about the aircraft at all; only the scene, the turbulence model and the camera
remain presentation choices.

**This reframes `Q-AV-8`.** The maintainer chose option (b) — defer `.mass`/`.run` behind
a real mass model — on the grounds that eigenvalues serve autopilot tuning, which is not
their use case. This feature is a *different* justification for the same work: not
control-law design, but **communicating a design's behaviour to its designer**. Worth
re-weighing if the feature is wanted.

## The renderer

`dutchroll_fpv.py` — pseudo-FPV frame + free-decay GIF.
`dutchroll_turb.py` — continuous-turbulence variant (the realistic case).

```bash
poetry run python dutchroll_fpv.py  out.gif <zeta> <fov_h_deg>
poetry run python dutchroll_turb.py out.gif <zeta> <wn> <roll_ratio>
```

**Camera model, derived not guessed.** Walksnail Avatar HD V2: 2.1 mm focal length,
160° FOV. A rectilinear (pinhole) lens at 160° would need a **23.8 mm** image circle —
impossible for any FPV sensor — so the optic is a fisheye and the renderer uses
**equidistant projection** (`r = f·θ`). That gives a 5.86 mm sensor diagonal (≈1/2″ to
1/1.8″, plausible) and, for a 16:9 crop, **139° horizontal / 78° vertical** (4:3 would be
128° / 96°). The 160° figure is therefore diagonal, not horizontal.

Why FOV matters: yaw produces image **translation**, which scales with pixels-per-degree,
so a wider lens makes the same yaw look *smaller*. Roll produces image **rotation**, which
is FOV-independent. Wide-angle therefore suppresses the yaw component optically and leaves
the motion reading as roll — it changes the *balance*, not just the size.

**Unvalidated assumptions, flagged rather than buried:** gust RMS 2.2° and gust
correlation time 0.35 s in the turbulence model. They scale amplitude, not the character
of the difference between damping levels. What the goggles display may also differ from
what the sensor captures (scaling, crop, headset optics) — for calibration only the
former matters, and it was not determined.

## Separate finding — not part of this proposal

`RV-7` in `stability_results` carries **`Cnb` = 4.27** and **`Cma` = +5.13** (positive,
i.e. statically unstable in pitch), with `mac = 0.140 m` and `neutral_point_x = 0.249 m`.
An RV-7's chord is over a metre; the Cessna row in the same table has a sensible
`mac = 1.387 m`. **The reference quantities are ~10× too small, which inflates the
coefficients by the same factor.** This matches the known failure mode where ASB reference
values are taken from the first wing in the list rather than the main wing — for an import
whose first surface is the horizontal tail, `mac` and `s_ref` come from the tail. Worth a
bug ticket in its own right; it is unrelated to dutch roll and would corrupt any stability
verdict for affected imports.
