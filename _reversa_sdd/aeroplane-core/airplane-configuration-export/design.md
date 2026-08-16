# airplane-configuration-export — Technical Design

> Use-case design, nested under the module [`aeroplane-core`](../design.md).
> Focuses on HOW the use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Full module-level endpoint contract: [`../contracts.md`](../contracts.md).

## Interface

### Service surface — `app/services/aeroplane_service.py` 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `get_aeroplane_airplane_configuration` | `(db: Session, aeroplane_uuid)` | `dict` | the `cad_designer` `AirplaneConfiguration` payload (l.252) |
| `_to_json_compatible` | `(value)` | JSON-safe value | recursive NumPy stripper (l.33-44) |

### REST surface — `app/api/v2/endpoints/aeroplane/base.py` 🟢

| Method | Path | Handler | Status codes |
|---|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/airplane_configuration` | `get_aeroplane_airplane_configuration` (l.261) | 200 · **422 when `total_mass_kg` is null** · 404 · 500 |

Response model: `AirplaneConfigurationResponse`.
`{aeroplane_id}` is the public UUID.

### Payload shape 🟢

The body is the `cad_designer` `AirplaneConfiguration` — the wings and fuselages
of the aeroplane expressed as topology objects in the **millimetre** world. Two
properties are contractual:

| Guarantee | Rule |
|---|---|
| Unit | **millimetres** throughout (`cad_designer` world), converted from the metre database at `scale = 1000.0` |
| Serialisability | contains no `np.ndarray` and no `np.generic`; `json.dumps` succeeds on the whole body |

## Main Flow

### F1 — Export (`get_aeroplane_airplane_configuration`, l.252+) 🟢

1. Resolve the aeroplane by UUID (`NotFoundError` → **404** if absent).
2. **Gate:** if `total_mass_kg is None` → raise `ValidationError` (→ **422**).
   No conversion is attempted (l.263-267). The gate is first precisely because
   step 3 is the expensive part.
3. Convert the wings and fuselages through
   `app/converters/model_schema_converters.py` into the `cad_designer`
   `AirplaneConfiguration` (mm world; `scale = 1000.0`).
4. Run `_to_json_compatible` over the result so no `np.ndarray` / `np.generic`
   survives.
5. Return the dict; the endpoint wraps it in `AirplaneConfigurationResponse`.

### F2 — NumPy stripping (`_to_json_compatible`, l.33-44) 🟢

```
_to_json_compatible(value):
    np.ndarray  -> value.tolist()
    np.generic  -> value.item()          # np.float64 -> float, np.int64 -> int
    dict        -> { k: _to_json_compatible(v) for k, v in value.items() }
    list        -> [ _to_json_compatible(v) for v in value ]
    tuple       -> [ _to_json_compatible(v) for v in value ]   (tuples flatten to lists via JSON)
    otherwise   -> value unchanged
```

The recursion is total over the container types the converter hub can emit.
NumPy values reach the payload because the conversion path shares code with the
AeroSandbox-facing converters, which work in NumPy arrays. 🟢

### F3 — The unit boundary 🟢

```
database / AeroSandbox world :  metres
cad_designer topology world  :  millimetres
conversion                   :  scale = 1000.0   (m -> mm)
```

The scaling lives inside the converter hub (ADR 0001). This use case passes the
scale through and performs no arithmetic of its own — a second scaling here
would be a silent 1000× error. 🟢

## Alternative Flows

- **Aeroplane not found:** `NotFoundError` → **404** with
  `{"error": {"code": "not_found", …}}` via `_raise_http_from_domain`
  (`base.py:52-67`).
- **Missing mass:** `ValidationError` → **422** `validation_error`, raised before
  conversion. 🟢
- **Aeroplane with a mass but no wings and no fuselages:** **rejected with 422**
  (`Q-AC-5`, maintainer-answered). 🟢 The CAD stack cannot accept it —
  `AirplaneConfiguration.__init__` evaluates `self.wings[0]` and raises
  `IndexError` — so exporting it would be a false success that defers the
  failure to whoever opens the file.
- **Conversion failure inside the hub** (e.g. an airfoil `.dat` that cannot be
  resolved): propagates as whatever the hub raises, and is caught by the
  handler's defensive `except Exception → 500`. 🟡 No specific mapping exists for
  conversion errors.
- **Unexpected exception in the handler:** defensive `except Exception → 500`. 🟢

## Dependencies

- **`app/converters/model_schema_converters.py`** — the conversion hub. It is
  shared with `cad-generation`, `aero-analysis`, `avl-integration` and
  `openvsp-import`, which is why this use case delegates rather than converting
  locally.
- **`cad_designer` topology classes** — `AirplaneConfiguration` and everything it
  composes. Frozen and read-only per ADR 0002.
- **[`aeroplane-crud`](../aeroplane-crud/design.md)** — supplies the resolved
  aeroplane and the `total_mass_kg` the gate reads.
- **`wing-design` / `fuselage-design`** — own the `WingModel` / `FuselageModel`
  rows being converted, and the geometry semantics this use case does not
  interpret.
- **`numpy`** — only as a type to strip; the use case performs no numerical work.
- **`app/core/exceptions.py`** — the `ServiceException` hierarchy.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| The mass gate is checked before conversion, not after | `aeroplane_service.py:263-267` | 🟢 |
| A missing mass is a **422 validation** error, not a 409 conflict or a 404 | `aeroplane_service.py:263-267`; `_raise_http_from_domain` | 🟢 |
| NumPy is stripped defensively at the service boundary rather than avoided upstream in the converters | `aeroplane_service.py:33-44` | 🟢 |
| Millimetres in CAD, metres in DB and AeroSandbox — converted only in `app/converters/` | ADR 0001 | 🟢 |
| Conversion is delegated to the shared hub so all five consumers stay identical | `model_schema_converters.py` used by five modules | 🟢 |
| The export is a pure read — no caching, no persisted artefact | no writes in the call path | 🟡 |

## Internal State

None. The use case is a stateless projection: it reads the `aeroplanes` row plus
its `wings` and `fuselages`, builds a payload in memory and returns it. Nothing
is persisted, cached or memoised, so every call re-runs the full conversion. 🟡

## Observability

- `logger.exception` on 5xx from the handler; 4xx are logged at INFO by the
  global handler (`app/main.py` error handlers). 🟢
- No metrics or traces — in particular there is **no timing instrumentation** on
  the conversion, even though it is the most expensive part of the route. 🟡
- No domain event is emitted on export. 🟢

## Risks and Gaps

- 🟢 **Completeness is validated: at least one lifting surface is required**
  (`Q-AC-5`). Rejected alternative: exporting with a `DesignWarning` — ADR 0020
  declares *substitutions*, not *broken outputs*, and warning that a file is
  unusable while still producing it leaves the user holding an artefact whose
  only correct use is to be discarded.
- 🟡 **Conversion failures gain a dedicated mapping.** User-fixable failures
  (unresolvable airfoil `.dat`, inconsistent station list) become an explicit
  `ValidationDomainError` → 422 with a remediation message; only genuine server
  faults stay 500 (`Q-AC-6`). Derived from the single-envelope ruling `Q-CC-3`
  rather than decided directly, so INFERRED until implemented.
- 🔴 **Caching the export payload is undecided.** Every request re-runs the full
  conversion, which shares code with the CAD and aero converters, and nothing
  guards against the route being polled. No question in the validation interview
  addressed this.
- 🟡 **`AeroplaneSchema.wings` is an `OrderedDict` whose first entry is not
  necessarily the main wing.** The main wing is derived as the largest planform
  area (gh-788 / gh-1092); consumers of this payload must not assume `wings[0]`.
- 🟡 **No caching.** Every request re-runs the full conversion, which shares code
  with the CAD/aero converters and is not cheap. Acceptable at current scale,
  but the route has no guard against being polled.
- 🟡 **The NumPy stripper is a symptom, not a fix.** It exists because the shared
  converter hub emits NumPy types; if the hub's return contract were tightened,
  the stripper would become dead code — and if the hub gains a new NumPy-bearing
  container type the stripper does not handle, serialisation breaks again.
