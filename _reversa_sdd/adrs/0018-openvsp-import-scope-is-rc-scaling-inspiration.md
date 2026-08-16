# ADR 0018 — OpenVSP import is "RC-scaling inspiration": geometry and mass only

- **Status:** Accepted — in force
- **Decided:** 2026-05/06 (epic gh-640; the scope call is recorded as "Variante B")
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (module docstrings, scaling behaviour, warning policy); the *scope rationale* is 🟡 (project memory + code comments)

## Context

OpenVSP is NASA's parametric geometry tool with a large public model library, so
importing gives a user realistic starting geometry in seconds. But an OpenVSP model
of a full-size aircraft is not an RC model: its propulsion definitions, inertia
tensors, control-surface group gains and VSPAERO setups are meaningless or actively
wrong once the airframe is scaled to a 1.5 m span and 2 kg, and importing them
faithfully would produce an aircraft whose numbers *look* authoritative and are not.
Hard technical facts had to be accommodated too: OpenVSP 3.50 removed
`SetLengthUnit` and the `LengthUnit` parm, so a file carries **no unit at all**.

## Decision

**Import the airframe, not the aircraft. Scope is explicitly "RC-scaling
inspiration": geometry and mass *positions* only.** Out of scope, deliberately:
propulsion, inertia, control-surface group gains, VSPAERO validation, and
leading-edge devices.

1. **Nothing aborts an import except three errors** — `ImportError` (openvsp
   missing), `FileNotFoundError`, and `ScaleValidationError`. Handler failures,
   post-pass failures, per-record persistence failures, undetectable units,
   unavailable or rejected slicer output and failed sewing **all degrade into
   structured warnings** reaching the frontend banner (gh-648). `ImportWarning`
   carries `component_type`, `component_name`, `reason` and
   `severity ∈ {info, warning, error}`; 14 unsupported geom types have a user-facing
   reason (PROP, DISK, MESH, CONFORMAL, HUMAN, POD, BOR, GEAR, …).
2. **Scaling never touches angles or masses.** `_scale_aeroplane_lengths` scales wing
   `xyz_le`/`chord`, `xyz_ref` and weight-item positions; twist is angular and masses
   are out of scope. A scaling run **always** appends an `info` warning stating that
   masses were left untouched.
3. **Source units are measured, not trusted** (gh-808). The importer exports the
   largest fuselage to STEP (which VSP writes metric), measures its bounding box, and
   **snaps** the implied ratio to `{m, yd, ft, in, cm, mm}` within a 2 % tolerance.
   No match ⇒ import unchanged.
4. **The handler schema is the authority, the slicer is a refinement.** Fuselage
   refinement runs only when the *handler* xsec positions are x-dominant
   (`extent_x ≥ 1.2·extent_y` and `≥ 1.2·extent_z`) — using the STEP bounding box
   instead would misread a `symmetric=True` geom as Y-dominant. The refined result is
   accepted only when `0.5 ≤ x_span(refined)/x_span(handler) ≤ 2.0` (gh-803);
   otherwise the handler wins.
5. **Airfoil resolution never raises.** Every VSP section shape has a path: NACA
   4/5/6/16-series generated as `.dat`, file airfoils exported verbatim, CST sampled
   with an info warning, anything unknown exported with a `vsp_imported_unknown` tag,
   and `naca0012.dat` as the last resort. Approximations are declared — the 6- and
   16-series carry an info warning saying t/c and design Cl are exact but the
   thickness shape is not conformal-mapped.
6. **Cross-validate offline, not in the product.** `scripts/vspaero_benchmark/` is a
   harness, not a runtime dependency.

## Consequences

- A real geometry lands in seconds and the user is told exactly what was lost — the
  warning banner is the product surface of the scope decision. Unit *measurement*
  fixed a class of silent 3.28× errors no file parsing could catch, and the
  cross-validation harness found **real application bugs**, most importantly F1/#788
  (`s_ref` taken from `wings[0]`, making every coefficient ≈8× wrong for a
  tail-first import). Validated against reality: AeroBuildup vs the measured DG-101G
  polar (max L/D ≈ 39 vs 38.3), ASB-VLM vs VSPAERO lift slope within 2–3 %.
- 🔴 **Two shipped features never run in production** — `openvsp_ss_control.register()`
  and `openvsp_validation.validate_geometry` are each referenced only from their
  tests, so imported aircraft silently arrive with **no control surfaces** and no
  geometry cross-check. Both fall under
  [ADR 0021](0021-complete-but-unreachable-code-is-deleted-by-default.md).
- 🔴 **Three open fidelity gaps:** #791 the importer loses airfoil camber (`C_L0`
  offset ≈ 0.43 on the DG-101G); #792 xsec augmentation makes ASB-VLM intractable at
  default resolution (215 s per solve — AeroBuildup, the app default, is unaffected);
  #814 the sewn solid is malformed at sharp fuselage fillets, corrupting the
  construction download.
- 🔴 `LEN_UNIT_TO_METERS` maps `LEN_UNITLESS → 1.0` (treated as metres) — a silent
  assumption on legacy files.
- **Warning-only failure means an import can be substantially lossy and still look
  successful.** The banner is the only signal; nothing blocks.
- **Process-level state** means `uvicorn --reload` does not pick up importer changes;
  restart and delete old imports before re-testing.
- **The scope decision is prose and comments only.** Nothing prevents a future
  contributor from importing propulsion data.

**Rejected:** full-fidelity import (authoritative-looking numbers that are wrong at RC
size are worse than no numbers); aborting on unsupported geometry (would reject
almost every real public model); using the sewn solid as the slicing source (tried
and reversed, gh-812); running VSPAERO in-product (the PyPI wheel ships without the
binaries).

## Related

[ADR 0012](0012-design-warnings-instead-of-silent-fallbacks.md) ·
[ADR 0017](0017-optional-heavy-dependencies-probed-at-import.md) ·
[ADR 0021](0021-complete-but-unreachable-code-is-deleted-by-default.md) ·
[ADR 0001 amendment](0001-millimetres-in-cad-metres-in-db-and-aerosandbox.md) (the
STEP unit mechanism) · domain rules BR-73 … BR-77 ·
[`../questions.md`](../questions.md) §Q-VI-1, §Q-VI-2.
Evidence: commits `c5c16fc7` (gh-640), `ab5324b8` (gh-788), `766a5fd2` (gh-803);
`scripts/vspaero_benchmark/FINDINGS.md`; project memory
`feedback_openvsp_import_rc_scope`.
