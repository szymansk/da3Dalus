# airplane-configuration-export — Implementation Tasks

> Executable sequence to re-implement the use case from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `aeroplanes` table with `total_mass_kg` and the UUID lookup available — see
      [`../aeroplane-crud/tasks.md`](../aeroplane-crud/tasks.md) T-01, T-05, T-09.
- [ ] `wings` and `fuselages` models available (modules `wing-design`,
      `fuselage-design`) — there is nothing to convert without them.
- [ ] `app/converters/model_schema_converters.py` available with the
      wing/fuselage → `AirplaneConfiguration` conversion at `scale = 1000.0`.
- [ ] `cad_designer` topology classes importable (`AirplaneConfiguration` and
      what it composes). Note these are frozen and read-only per ADR 0002.
- [ ] `app/core/exceptions.py` hierarchy (`NotFoundError`, `ValidationError`) and
      the global error-envelope handler.
- [ ] `numpy` available — only as a type to strip.

## Tasks

- [ ] **T-01 — `_to_json_compatible` NumPy stripper.**
  Recursively map `np.ndarray → list` (via `.tolist()`), `np.generic → `Python
  scalar (via `.item()`), recursing into dicts, lists and tuples; pass every
  other value through unchanged.
  - Legacy origin: `app/services/aeroplane_service.py:33-44`
  - Definition of done: a payload containing `np.float64`, `np.int64` and a
    nested `np.ndarray` inside a dict-of-lists round-trips through `json.dumps`
    without error, and the types in the result are plain Python types.
  - Confidence: 🟢

- [ ] **T-02 — The mass gate.**
  Raise `ValidationError` when `total_mass_kg is None`, **before** any conversion
  is attempted.
  - Legacy origin: `app/services/aeroplane_service.py:263-267`
  - Definition of done: with the converter hub patched to raise on any call, a
    mass-less aeroplane still returns **422** — proving the gate runs first.
  - Confidence: 🟢

- [ ] **T-03 — `get_aeroplane_airplane_configuration` assembly.**
  Resolve by UUID → gate on the mass → convert wings and fuselages through the
  converter hub at `scale = 1000.0` → run `_to_json_compatible` → return the
  dict.
  - Legacy origin: `app/services/aeroplane_service.py:252, 263-267`
  - Definition of done: a complete aeroplane returns a payload whose geometry is
    in millimetres and whose body survives `json.dumps`.
  - Confidence: 🟢

- [ ] **T-04 — Delegate conversion to the shared hub.**
  Call `app/converters/model_schema_converters.py`; do **not** reimplement wing
  or fuselage conversion, and do **not** scale anything locally.
  - Legacy origin: `app/converters/model_schema_converters.py` (shared with
    `cad-generation`, `aero-analysis`, `avl-integration`, `openvsp-import`)
  - Definition of done: a grep of this use case's code contains no literal
    `1000` or `0.001`; a wing stored with `chord = 0.25` m appears as `250` in
    the payload.
  - Confidence: 🟢

- [ ] **T-05 — REST route and error mapping.**
  `GET /aeroplanes/{aeroplane_id}/airplane_configuration` returning
  `AirplaneConfigurationResponse`; `NotFoundError → 404 not_found`,
  `ValidationError → 422 validation_error`, defensive
  `except Exception → 500`.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/base.py:52-67, 261`
  - Definition of done: contract tests assert 200, 404 and 422 with the exact
    envelope `{"error": {"code": …, "message": …, "details": …}}`.
  - Confidence: 🟢

- [ ] **T-06 — Decide the empty-aircraft contract.**
  Today an aeroplane with a mass but no wings and no fuselages exports an empty
  configuration with a 200. Either add a completeness check (→ 422) or document
  the permissive behaviour deliberately.
  - Legacy origin: absence of any surface check in
    `app/services/aeroplane_service.py:252-280`
  - Definition of done: the chosen behaviour is covered by a test asserting the
    status code for a surface-less aeroplane.
  - Confidence: 🟢 — decided (`Q-AC-5`): require at least one lifting surface,
    reject with 422.

- [ ] **T-07 — Decide the conversion-failure contract.**
  Errors raised inside the converter hub (unresolvable airfoil `.dat`,
  inconsistent station list) currently surface as a generic **500**. Map the
  user-fixable subset to 422 or document the current behaviour.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/base.py:261` (defensive
    `except Exception → 500` with no conversion-specific branch)
  - Definition of done: a conversion error triggered by bad user data produces
    the agreed status code, asserted by a test.
  - Confidence: 🟡 — direction derived from `Q-CC-3` (`Q-AC-6`): user-fixable
    conversion failures become `ValidationDomainError` → 422; server faults stay
    500.

## Test Tasks

- [ ] **TT-01 — Happy path: create → populate → export.** Create an aeroplane,
      add a wing and a fuselage, set the mass, fetch `airplane_configuration`,
      assert 200 and JSON-serialisability (see
      [`requirements.md`](requirements.md) Acceptance Criteria).
- [ ] **TT-02 — Failure: export without a mass returns 422** with
      `error.code == "validation_error"`.
- [ ] **TT-03 — Gate ordering:** with the converter hub patched to raise, a
      mass-less aeroplane still returns 422 rather than 500 (guards T-02).
- [ ] **TT-04 — Unknown UUID returns 404** with the `not_found` envelope.
- [ ] **TT-05 — NumPy stripping matrix:** `np.ndarray`, `np.float64`, `np.int64`,
      nested inside dicts, lists and tuples; assert `json.dumps` succeeds and the
      result contains only plain Python types.
- [ ] **TT-06 — Unit boundary:** a wing stored at `chord = 0.25` m appears as
      `250` in the payload — a regression guard against a double or missing
      `scale = 1000.0`.
- [ ] **TT-07 — Order preservation:** two wings appear in stored order, and the
      test explicitly does **not** assert that `wings[0]` is the main wing
      (gh-788 / gh-1092).
- [ ] **TT-08 — Read-only guarantee:** the route issues no `INSERT`, `UPDATE` or
      `DELETE`, verified with a statement spy.

## Data Migration Tasks

None. This use case is a pure read-time projection and persists nothing. 🟢

## Suggested Order

1. **T-01** first — the stripper is a pure function, testable in isolation and
   independent of everything else in the use case.
2. **T-02** next; it only needs the aeroplane lookup from
   [`aeroplane-crud`](../aeroplane-crud/tasks.md) T-05 and can be validated with
   the conversion stubbed out entirely.
3. **T-04** blocks **T-03**: the assembly is meaningless until the converter hub
   exists, and the hub in turn needs `wing-design` / `fuselage-design`.
4. **T-03** once T-01, T-02 and T-04 are in place — it is the composition of the
   three.
5. **T-05** last — the REST layer is thin and only wires what is already tested.
6. **T-06** and **T-07** are decisions, not dependencies; they can land at any
   point once the product questions in Pending Gaps are answered.

## Resolved by the validation interview (2026-08-15)

- 🟢 **An empty `AirplaneConfiguration` is not legal** (`Q-AC-5`): the export
  requires at least one lifting surface and returns 422 otherwise.
- 🟢 **`_to_json_compatible` stays — as a throwing assertion, not a stripper**
  (`Q-AC-9`). The converter hub is tightened to return JSON-native types (one
  authority, ADR 0022) **and** the check remains in place, but encountering a
  non-native type now raises, naming the field and type, instead of silently
  repairing it. Repairing was an undeclared fallback (ADR 0020) that hid the
  hub's defect; the assertion is a guard, not a second producer — the same shape
  as the `lazy="raise"` relationship in `Q-AF-7`.
- 🟡 **Conversion failures** become `ValidationDomainError` → 422 when
  user-fixable, 500 only for genuine server faults (`Q-AC-6`, derived from
  `Q-CC-3`).

## Pending Gaps (🔴)

- **Should the payload be cached?** Every request re-runs the full conversion,
  which shares code with the CAD and aero converters. There is no guard against
  the route being polled. **Not addressed by the validation interview** — this
  remains an open product question.
