# AVL Strip Forces — Design Spec

## Context

GH #40 requests aerodynamic distribution endpoints (lift, moment). AVL
computes spanwise strip forces internally but Aerosandbox's `asb.AVL`
wrapper doesn't expose them — it only returns aggregate coefficients.

This spec adds a subclass of `asb.AVL` that extends the keystroke
sequence to capture strip-force data, and a new REST endpoint to serve
spanwise distributions.

## Architecture

### New class: `AVLWithStripForces(asb.AVL)`

**File:** `app/services/avl_strip_forces.py`

Subclasses `asb.AVL` with three overrides:

1. **`_default_keystroke_file_contents()`** — appends `fs` (strip
   forces) command after the existing `st` (stability) output, writing
   to a second output file (`strip_forces.txt`).

2. **`run()`** — calls `super().run()` for the standard result dict,
   then parses the strip-force file and adds a `strip_forces` key.

3. **`_parse_strip_forces(filepath: str) -> list[dict]`** — new static
   method that parses AVL's tabular strip-force output into a list of
   dicts.

### Data flow

```
asb.Airplane → AVLWithStripForces.run()
  → writes .avl input (inherited)
  → sends extended keystrokes (st + fs)
  → parses stability output (inherited)
  → parses strip-force output (new)
  → returns dict with strip_forces: [{y, chord, cl, cd, cm, ...}, ...]
```

### Integration

**`app/api/utils.py`** — when analysis_tool is AVL, use
`AVLWithStripForces` instead of `asb.AVL`. The standard result dict
is unchanged; the extra `strip_forces` key is optional and ignored
by the existing `AnalysisModel.from_avl_dict()` until explicitly
consumed.

**New endpoint:**
```
GET /aeroplanes/{id}/wings/{name}/strip_forces
```
Runs AVL analysis, extracts strip_forces for the requested wing,
returns the distribution data.

### Schema

```python
class StripForceEntry(BaseModel):
    y_span: float        # spanwise position (m)
    chord: float         # local chord (m)
    cl: float            # local lift coefficient
    cd: float            # local drag coefficient
    cm: float            # local moment coefficient
    cl_norm: float       # normalized Cl (Cl * chord / Cref)

class StripForcesResponse(BaseModel):
    wing_name: str
    strips: list[StripForceEntry]
    reference: StripForceReference

class StripForceReference(BaseModel):
    alpha: float
    mach: float
    sref: float
    cref: float
    bref: float
```

### Key files

| File | Change |
|------|--------|
| `app/services/avl_strip_forces.py` | New — AVLWithStripForces subclass |
| `app/schemas/strip_forces.py` | New — Pydantic schemas |
| `app/api/v2/endpoints/aeroanalysis.py` | New endpoint |
| `app/api/utils.py` | Swap asb.AVL → AVLWithStripForces |
| `app/tests/test_avl_strip_forces.py` | New — unit tests |
| `app/tests/test_avl_strip_forces_integration.py` | New — slow integration test |

### Tests

1. **Unit: Strip-Force Parser** — fixed AVL output string → correct
   StripForceEntry list. Verifies column parsing, edge cases (empty
   output, malformed lines).

2. **Unit: Keystroke Extension** — asserts `fs` and `strip_forces.txt`
   appear in the keystroke sequence; asserts all parent keystrokes are
   preserved.

3. **Integration: AVL Roundtrip** (slow) — eHawk model →
   AVLWithStripForces.run() → strip_forces is non-empty, values are
   physically plausible (Cl > 0 for positive alpha, y_span within
   wingspan).

4. **Endpoint Test** — GET strip_forces → 200, response matches
   StripForcesResponse schema, strips list is non-empty.

### Risks & mitigations

- **Aerosandbox updates change `_default_keystroke_file_contents()`
  signature** — unlikely (stable since years), but if it happens the
  subclass override will simply fail loudly at import time. Pinned
  dependency version mitigates further.

- **AVL strip-force output format varies** — parser should be lenient
  with whitespace but strict on column order. Unit test with real AVL
  output sample locks the expected format.

- **Upstream PR accepted** — if Aerosandbox adds strip-force support
  natively, we delete the subclass and use theirs. The endpoint and
  schemas remain unchanged.
