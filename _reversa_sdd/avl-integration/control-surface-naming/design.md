# control-surface-naming — Technical Design

> Focuses on HOW this use case is built, read from the legacy code.
> Parent module design: [`../design.md`](../design.md).
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Interface

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_DUAL_ROLE_AXES` | `dict[str, tuple[str, str]]` | — | `elevon/flaperon/ruddervator` → `(primary, secondary)` 🟢 |
| `PRIMARY_AXES` / `SECONDARY_AXES` | `set[str]` | — | `{pitch, lift}` / `{roll, yaw}` 🟢 |
| `axis_control_name` | `(role, axis, wing_key, xsec_index)` | `str` | `[{role}]{axis}_{sanitize(wing_key)}_{i}` 🟢 |
| `assert_unique_control_names` | `(names: Iterable[str])` | `None` / raises `ValueError` | across surfaces 🟢 |
| `ControlAxis` | dataclass | — | `name`, `sgn_dup`, `gain`, `symmetric`, `hinge_point`, `deflection`, `role`, `axis` 🟢 |
| `_ROLE_TAG_RE` | `^\[(\w+)\](.*)$` | — | parses a tagged name back to its role 🟢 |

No HTTP surface. This use case is a pure library shared by three consumers.

## Main Flow — decomposing one surface

```
resolve_axes(role, wing_key, xsec_index, deflection, hinge_point,
             mix_gain_primary, mix_gain_secondary):

  if role in _DUAL_ROLE_AXES:
      primary, secondary = _DUAL_ROLE_AXES[role]
          elevon      → (pitch, roll)
          flaperon    → (lift,  roll)
          ruddervator → (pitch, yaw)

      yield ControlAxis(
          name       = axis_control_name(role, primary, wing_key, xsec_index),
          axis       = primary,                     # ∈ PRIMARY_AXES  {pitch, lift}
          sgn_dup    = +1.0,                         # SYMMETRIC
          gain       = mix_gain_primary,
          symmetric  = True,
          hinge_point= hinge_point,
          deflection = deflection,                   # the surface's own deflection
          role       = role,
      )
      yield ControlAxis(
          name       = axis_control_name(role, secondary, wing_key, xsec_index),
          axis       = secondary,                    # ∈ SECONDARY_AXES {roll, yaw}
          sgn_dup    = −1.0,                         # ANTISYMMETRIC
          gain       = mix_gain_secondary,
          symmetric  = False,
          hinge_point= hinge_point,
          deflection = 0.0,                          # ← load-bearing, see below
          role       = role,
      )
  else:
      yield the existing single-axis ControlAxis verbatim
            (existing tagged name, ±1 sign unchanged)      # l.134-146
```

### Why the secondary baseline is `0.0` 🟢

The same `ControlAxis` list is handed to **both** the AVL builder and the
AeroSandbox airplane builder. AeroSandbox models a **single** axis per control
surface, so if the antisymmetric axis carried a non-zero baseline the ASB
fallback would silently apply a roll/yaw deflection as if it were symmetric.
Setting it to zero is what makes one list safe for two solvers with different
capabilities (ADR 0003, negative consequence: "dual-role surfaces are degraded on
the default path").

## Naming 🟢

```
axis_control_name(role, axis, wing_key, xsec_index)
    → f"[{role}]{axis}_{sanitize(wing_key)}_{xsec_index}"

examples:  [ruddervator]pitch_htail_1
           [elevon]roll_wing_2
           [flaperon]lift_wing_0

_ROLE_TAG_RE = ^\[(\w+)\](.*)$      # "[elevon]roll_wing_2" → role "elevon"
```

The role tag is not decoration: `_detect_control_capabilities` in
`mission-and-sizing` classifies an ASB airplane's controls into
`has_pitch_control` / `has_roll_control` / `has_yaw_control` / `has_flap`
**purely from the tag**, without a database round-trip. That is why the tag must
survive every transformation of the name.

## Uniqueness 🟢

```
build_avl_geometry_file(...):
    per surface:  dedup control names WITHIN the surface
                  (a control is deliberately repeated on sections i and i+1 —
                   panel-strip interpolation)
    across surfaces: assert_unique_control_names(all names)
                     → ValueError on ANY duplicate, BEFORE any text is produced
```

Rationale, recorded in the code: **AVL silently collapses identically named
`CONTROL` variables into a single DOF** (avl_doc 778-789). Two unrelated
surfaces sharing a name would move together, with no error from AVL, no
diagnostic in the output, and a plausible-looking result. This assertion is the
only defence.

## The #955 divergence 🔴

```
                    ┌──────────────────────────────┐
                    │  control_surface_mixing      │  ← the canonical names
                    │  "[ruddervator]pitch_htail_1"│
                    └──────────────┬───────────────┘
             ┌─────────────────────┼──────────────────────┐
             ▼                     ▼                      ▼
   AVL geometry builder    ASB airplane builder    trim_enrichment_service
        ✅ uses it              ✅ uses it            ❌ `controls` uses it
                                                      ❌ `limits` uses ted.name

                            retrim_service._find_pitch_control_name
                                ❌ returns ted.name  (works only because the
                                   trim service re-resolves role/display names)

                            stability_service._find_trim_elevator
                                ❌ substring match on "elevator"
```

Consequences on any dual-role aircraft (V-tail, elevon, flaperon):

1. `limits.get(surface_name, (25.0, 25.0))` **misses**, so
   `usage_fraction = |δ| / 25.0` is computed against a hard-coded limit rather
   than the aircraft's real hinge limit. A surface with ±12° travel trimmed to
   10° reports 40 % usage instead of 83 % — the authority warning never fires.
2. The gh-863 union (`dict.fromkeys(limits, 0.0) | controls`) injects a
   **phantom surface at 0°** under the DB name that no solver ever trims, which
   then appears in `deflection_reserves` and `mixer_values`.
3. `trim_elevator_deg` is `NULL` on the stability row, because
   `"[ruddervator]pitch_htail_1"` does not contain `"elevator"`.
4. The background retrim survives only because
   `aerobuildup_trim_service` re-resolves display and role names; if that
   re-resolution ever changed, every dual-role aircraft would stop re-trimming
   with only a log line.

**The fix**: key `limits` by `axis_control_name`, resolve the pitch control
through the axis decomposition rather than a substring match, and make the
lookup miss **loud** (a `DesignWarning`) rather than falling back silently.

## Alternative Flows

- **`role is None`** (a partial patch on a TED). The mixing-field validation in
  `wing-design` skips the role gate entirely; this use case is not invoked. 🟢
- **A single-axis role.** One `ControlAxis`, tagged name and sign preserved
  verbatim — no renaming, so existing aircraft are unaffected by gh-772. 🟢
- **A wing key with spaces or punctuation.** `sanitize` normalises it so the
  emitted name is AVL-safe. 🟢
- **A duplicate name across surfaces.** `ValueError` before any file text
  exists. 🟢
- **A duplicate within one surface.** Deduped, not an error — panel-strip
  duplication is intentional. 🟢
- **A name that has already been tagged.** `_ROLE_TAG_RE` extracts the role; the
  name is not re-tagged. 🟡 (inferred from the regex's existence and the
  single-axis passthrough)

## Dependencies

- **`wing-design`** — the TED role vocabulary, `hinge_point`,
  `mix_gain_primary` / `mix_gain_secondary`, `differential_ratio`, and the
  role-gating validation (`DUAL_ROLE_VALUES`, `DIFFERENTIAL_ROLE_VALUES`).
- **[`../avl-geometry-generation/`](../avl-geometry-generation/requirements.md)**
  — consumer: emits one `CONTROL` block per `ControlAxis`.
- **`aero-analysis` (`model_schema_converters`)** — consumer: builds the ASB
  airplane's control surfaces from the same list.
- **`aero-analysis` (`trim_enrichment_service`)** — consumer, **currently
  broken** (#955).
- **`mission-and-sizing` (`operating_point_generator_service`)** — consumer of
  the role **tag** for capability gating.
- Nothing else: no DB, no solver, no binary.

## Identified Design Decisions

| Decision | Evidence in code | Confidence |
|---|---|---|
| Three roles are dual, everything else is single-axis | `_DUAL_ROLE_AXES:29-33` | 🟢 |
| Primary = symmetric (+1), secondary = antisymmetric (−1) | `PRIMARY_AXES` / `SECONDARY_AXES` | 🟢 |
| The antisymmetric baseline is forced to `0.0` so one list serves both solvers | gh-772 | 🟢 |
| Single-axis roles keep their name and sign verbatim, so gh-772 is backwards-compatible | l.134-146 | 🟢 |
| The role is embedded in the name as a parseable tag | `_ROLE_TAG_RE:25` | 🟢 |
| Uniqueness asserted before any geometry is written | `assert_unique_control_names:149-164` | 🟢 |
| Dedup per surface, assert across surfaces | `build_avl_geometry_file` | 🟢 |
| `SgnDup` is a flag; `differential_ratio` is reporting-only | `control_surface_mixing.py:14-15` | 🟢 |
| One module owns the rule (ADR 0008) | shared by three builders | 🟢 |
| Three services still key on the DB name | `trim_enrichment_service:72-118`, `retrim_service`, `stability_service` | 🔴 (#955) |

## Internal State

None. Pure functions over primitives; `ControlAxis` is an immutable value
object. This is deliberate — it is why the rule can be shared by three modules
without a coordination problem. 🟢

## Observability

- `ControlAxis` records `role`, `axis`, `sgn_dup`, `gain`, `symmetric`,
  `hinge_point` and `deflection`, so any name can be explained back to its
  source. 🟢
- The uniqueness `ValueError` names the colliding string. 🟢
- 🔴 **A limits lookup miss is invisible.** `limits.get(name, (25.0, 25.0))`
  returns a plausible default, so the failure surfaces only as a *wrong number*,
  never as an error, a warning or a log line. This is the single most damaging
  observability gap in the cluster: the system reports control authority
  confidently and incorrectly.
- 🔴 A `NULL` `trim_elevator_deg` is indistinguishable from "this aircraft has no
  pitch control".

## Risks and Gaps

- 🔴 **#955 — three consumers key on the DB name.** Fix all three together;
  fixing one leaves the aircraft in a half-consistent state where, for example,
  the reserve is right but the phantom surface remains.
- 🔴 **The `(25.0, 25.0)` fallback is silent and plausible.** Per ADR 0012 a
  fallback should be a visible design warning. At minimum, a reserve computed
  against the default should be flagged.
- 🔴 **The retrim works by accident.** `_find_pitch_control_name` returns the DB
  name and only survives because `aerobuildup_trim_service` re-resolves
  display/role names. That coupling is undocumented and untested.
- 🟡 **`trim_elevator_deg` presumes a conventional elevator** in its very column
  name, which encodes the same assumption that #955 violates.
- 🟡 **Re-tagging an already-tagged name** is not explicitly guarded; the regex
  exists to parse tags back out, but nothing asserts a name is tagged at most
  once.
- 🟡 **`sanitize` is not specified in the analysis.** Which characters it strips
  or replaces matters, because two wing names differing only in punctuation could
  sanitise to the same key and produce a spurious uniqueness collision — or,
  worse, a real collision that the assertion catches only by luck of ordering.
