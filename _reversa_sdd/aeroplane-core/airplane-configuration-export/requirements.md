# airplane-configuration-export

> Use-case specification, nested under the module [`aeroplane-core`](../requirements.md).
> Focuses on WHAT the use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: aeroplane-core,
> ADR 0001 (millimetres in CAD, metres in DB and AeroSandbox).

## Overview

`airplane-configuration-export` is the **single handover point from the
persistence world into the CAD world**. It assembles the stored wings and
fuselages into the `cad_designer` `AirplaneConfiguration` payload, refuses to do
so without a design mass, and guarantees the result is plain JSON — no NumPy
types survive. It crosses the metre→millimetre unit boundary in exactly one
place. 🟢

## Responsibilities

- Resolve an aeroplane by UUID and gate the export on `total_mass_kg`. 🟢
- Convert the aeroplane's wings and fuselages into the `cad_designer`
  `AirplaneConfiguration` topology via the converter hub. 🟢
- Apply the metre→millimetre scale (`scale = 1000.0`) at that boundary and
  nowhere else. 🟢
- Strip every `np.ndarray` / `np.generic` from the assembled payload so it is
  JSON-serialisable. 🟢
- Return the payload wrapped in `AirplaneConfigurationResponse`. 🟢

**Explicitly NOT this use case's responsibility:** aeroplane lifecycle and the
mass upsert itself (→ [`aeroplane-crud`](../aeroplane-crud/requirements.md));
wing and fuselage geometry semantics (→ modules `wing-design`,
`fuselage-design`); building the actual CAD solid (→ module `cad-generation`);
the component tree (→ [`component-tree`](../component-tree/requirements.md)).

## Business Rules

- **BR-CE1 — The export requires a mass, and fails before doing any work.** 🟢
  *(refines module rule BR-A4.)* A missing `total_mass_kg` raises
  `ValidationError` → **HTTP 422** *before* any conversion is attempted
  (`app/services/aeroplane_service.py:263-267`). The gate is deliberately placed
  first: the conversion is the expensive part.
- **BR-CE2 — No NumPy in the CAD payload.** 🟢 *(refines BR-A5.)*
  `_to_json_compatible` recursively converts `np.ndarray → list` and
  `np.generic →` Python scalars, recursing into dicts, lists and tuples
  (`aeroplane_service.py:33-44`). Without it the response cannot be serialised.
- **BR-CE3 — The payload is the millimetre world.** 🟢 The `cad_designer`
  topology classes speak **millimetres** while the database speaks **metres**;
  the conversion happens in `app/converters/model_schema_converters.py` with
  `scale = 1000.0` (ADR 0001). This use case must not scale anything itself.
- **BR-CE4 — The converter hub is the only conversion path.** 🟢
  `app/converters/model_schema_converters.py` is shared with `cad-generation`,
  `aero-analysis`, `avl-integration` and `openvsp-import`; this use case calls
  into it rather than reimplementing wing/fuselage conversion.
- **BR-CE5 — Read-only.** 🟢 The export performs no writes and no flush; it is a
  pure projection of stored state. 🟡 INFERRED from the absence of any `db.add()`
  / `db.flush()` in the call path.
- **BR-CE6 — `wings` is an `OrderedDict` whose first entry is not the main
  wing.** 🟡 Insertion order is preserved, but the main wing is derived as the
  largest planform area (gh-788 / gh-1092). Consumers must not assume
  `wings[0]`, and this use case makes no claim about ordering semantics.
- **BR-CE7 — Domain errors map to the module envelope.** 🟢 `NotFoundError` →
  404 `not_found`; `ValidationError` → 422 `validation_error`; unexpected →
  500, via `_raise_http_from_domain` (`base.py:52-67`).
- 🟢 **The export requires at least one lifting surface** (`Q-AC-5`,
  maintainer-answered). The precondition is two-part — the mass gate **and** a
  surface check — because the export contract is *"produces a loadable
  `AirplaneConfiguration`"*, not *"produces JSON"*. Today an aeroplane with a
  mass but no wings and no fuselages exports successfully while
  `AirplaneConfiguration.__init__` evaluates `self.wings[0]` and raises
  `IndexError`, so the file cannot be loaded by the library it is written for.
  Rejection is a `ValidationDomainError` → **422**: the submitted design is
  internally incomplete and nothing in persisted state conflicts (`Q-FD-1`).

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-07 | Assemble and return the `AirplaneConfiguration` CAD payload *(module RF-07)* | Must | `GET .../airplane_configuration` → 200 with a JSON-serialisable body containing no NumPy types |
| RF-08 | Reject the export when `total_mass_kg` is unset *(module RF-08)* | Must | Aeroplane without mass → 422 `validation_error`, and no conversion is attempted |
| RF-CE-25 | Resolve the aeroplane by public UUID and 404 on an unknown one | Must | Unknown UUID → 404 `not_found` |
| RF-CE-26 | Convert wings and fuselages through the shared converter hub into the millimetre world | Must | A wing stored with `chord = 0.25` m appears in the payload as `250` mm |
| RF-CE-27 | Guarantee the response body survives `json.dumps` unchanged | Must | A payload containing `np.float64` and `np.ndarray` round-trips through `json.dumps` without error |
| RF-CE-28 | Preserve wing and fuselage insertion order without asserting which is the main surface | Should | Two wings appear in stored order; nothing in the payload marks `wings[0]` as the main wing |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | The CAD payload must be free of NumPy scalars and arrays before it leaves the service | `app/services/aeroplane_service.py:33-44` | 🟢 |
| Correctness | The mass gate runs before conversion, so an invalid aircraft costs no conversion work | `app/services/aeroplane_service.py:263-267` | 🟢 |
| Correctness | Unit conversion happens only inside the converter hub, at `scale = 1000.0` | `app/converters/model_schema_converters.py`; ADR 0001 | 🟢 |
| Reliability | The route is read-only; a failure leaves no partial state | `app/db/session.py:55-64` (ADR 0009), no writes in the call path | 🟡 |
| Security | No application-level authentication; the deployment tunnel is the trust boundary | ADR 0016 | 🟢 |

## Acceptance Criteria

```gherkin
Feature: AirplaneConfiguration export

  Scenario: Export succeeds for a fully specified aircraft
    Given an aeroplane with total_mass_kg 2.4, one wing and one fuselage
    When I GET /aeroplanes/{id}/airplane_configuration
    Then the response status is 200
    And the payload is JSON-serialisable with no numpy types
    And the wings and fuselages are present in the payload

  Scenario: Export refuses without a mass
    Given an aeroplane whose total_mass_kg is null
    When I GET /aeroplanes/{id}/airplane_configuration
    Then the response status is 422
    And the error code is "validation_error"
    And no wing or fuselage conversion was attempted

  Scenario: Export of an unknown aeroplane
    Given no aeroplane with the requested UUID
    When I GET /aeroplanes/{id}/airplane_configuration
    Then the response status is 404
    And the error code is "not_found"

Feature: Unit boundary

  Scenario: Geometry is delivered in millimetres
    Given a wing whose stored root chord is 0.25 metres
    When I GET /aeroplanes/{id}/airplane_configuration
    Then the corresponding chord in the payload is 250
    # the database stores metres, the cad_designer topology speaks millimetres

Feature: JSON compatibility

  Scenario: NumPy values are stripped before serialisation
    Given a conversion result containing an np.ndarray and an np.float64
    When the payload is assembled
    Then the ndarray has become a list
    And the np.float64 has become a Python float
    And json.dumps succeeds on the whole payload
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Assemble and return the payload (RF-07) | Must | The only handover into the CAD stack — `cad-generation` has no other source |
| Mass gate before conversion (RF-08, BR-CE1) | Must | A mass-less aircraft cannot be built; failing late would waste the expensive conversion |
| NumPy stripping (RF-CE-27, BR-CE2) | Must | Without it the response cannot be serialised at all — this is a hard failure, not a degradation |
| Conversion through the shared hub at `scale = 1000.0` (RF-CE-26) | Must | Wrong by 1000× when omitted; the hub is shared with four other modules so divergence here corrupts them all |
| 404 on an unknown UUID (RF-CE-25) | Must | Consistent with every other route in the module |
| Order preservation without main-wing semantics (RF-CE-28) | Should | Convenience; the main wing is derived from planform area downstream (gh-788) |
| Validating that the aircraft actually has surfaces | **Must** | 🟢 decided (`Q-AC-5`) — at least one lifting surface is required; 422 otherwise. Not yet implemented — an empty configuration still exports successfully today |
| Reimplementing wing/fuselage conversion locally | Won't | Deliberately delegated to the converter hub; a second implementation would drift |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/api/v2/endpoints/aeroplane/base.py` | `get_aeroplane_airplane_configuration` (l.261), `_raise_http_from_domain` (l.52-67) | 🟢 |
| `app/services/aeroplane_service.py` | `get_aeroplane_airplane_configuration` (l.252, gate l.263-267), `_to_json_compatible` (l.33-44) | 🟢 |
| `app/converters/model_schema_converters.py` | wing / fuselage → `AirplaneConfiguration` conversion, `scale = 1000.0` | 🟢 |
| `cad_designer/airplane/aircraft_topology/` | `AirplaneConfiguration` and the topology classes it composes (mm world) | 🟢 read-only (ADR 0002) |
| `app/schemas/` | `AirplaneConfigurationResponse` | 🟢 |
