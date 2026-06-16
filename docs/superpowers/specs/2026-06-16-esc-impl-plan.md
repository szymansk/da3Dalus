# ESC Component Model Enrichment — TDD Implementation Plan

**Date:** 2026-06-16
**Issue:** gh-1009
**Branch:** feat/gh-1009-esc-component-enrichment

---

## 1. Canonical ESC `specs` Schema (English labels)

Ordered as they should appear in the registry and UI:

| # | Field key | Label | Type | Unit | required | Notes |
|---|---|---|---|---|---|---|
| 1 | `continuous_current_a` | Continuous Current | number | A | no | was "Dauerstrom" |
| 2 | `max_current_a` | Burst Current | number | A | **yes** | was "Max Strom (kurz)" |
| 3 | `cells_lipo_min` | LiPo Cells Min | number | S | no | keep |
| 4 | `cells_lipo_max` | LiPo Cells Max | number | S | no | keep |
| 5 | `cells_nixx_min` | NiXX Cells Min | number | cells | no | **new** |
| 6 | `cells_nixx_max` | NiXX Cells Max | number | cells | no | **new** |
| 7 | `cells_liion_min` | Li-Ion/LiHV Cells Min | number | S | no | **new** |
| 8 | `cells_liion_max` | Li-Ion/LiHV Cells Max | number | S | no | **new** |
| 9 | `bec_voltage_5v` | BEC 5.0 V | boolean | — | no | new; replaces bec_voltage_v / bec_output |
| 10 | `bec_voltage_5_5v` | BEC 5.5 V | boolean | — | no | new |
| 11 | `bec_voltage_6v` | BEC 6.0 V | boolean | — | no | new |
| 12 | `bec_voltage_6_5v` | BEC 6.5 V | boolean | — | no | new |
| 13 | `bec_voltage_7_4v` | BEC 7.4 V | boolean | — | no | new |
| 14 | `bec_voltage_8_4v` | BEC 8.4 V | boolean | — | no | new |
| 15 | `bec_voltage_9v` | BEC 9.0 V | boolean | — | no | new |
| 16 | `bec_voltage_12v` | BEC 12.0 V | boolean | — | no | new |
| 17 | `bec_current_a` | BEC Current | number | A | no | keep |
| 18 | `protocol` | Protocol | enum | — | no | options unchanged: pwm/oneshot/dshot150/dshot300/dshot600 |
| 19 | `art_no` | Article No. | string | — | no | was "Art.-Nr." |

**Removed fields:** `cells` (legacy single), `bec_voltage_v` (scalar), `bec_output` (free string).

Dimensions (`bbox_x/y/z_mm`) live on the component row — not in specs. They are surfaced in the UI separately (see §6).

---

## 2. Migration Data-Transform Rules

### 2.1 `bec_output` (free-text string) → BEC voltage toggles

Parse defensively. The AVICON/Antares strings seen in dpower.json:

| bec_output value | bec_voltage_* booleans | bec_current_a |
|---|---|---|
| `"5V/6V 4A"` | `bec_voltage_5v=true`, `bec_voltage_6v=true` | 4 |
| `"5V/6V 8A"` | `bec_voltage_5v=true`, `bec_voltage_6v=true` | 8 |
| `"5V / 8A"` | `bec_voltage_5v=true` | 8 |
| `"5.0V, 5.5V, 6V einstellbar - 5A"` | `bec_voltage_5v=true`, `bec_voltage_5_5v=true`, `bec_voltage_6v=true` | 5 |
| `null` | (all false / absent) | — |

**Parse algorithm** (to be implemented in `_migrate_bec_output(raw: str) -> dict`):

1. Extract all voltage tokens matching `\d+\.?\d*\s*V` (case-insensitive), strip whitespace.
2. Snap each parsed voltage to the nearest standard value in {5.0, 5.5, 6.0, 6.5, 7.4, 8.4, 9.0, 12.0} with tolerance ±0.1 V.
3. Set the matching `bec_voltage_*` key to `True`.
4. Extract current with `(\d+)\s*A`; if found set `bec_current_a`.
5. If no voltage or current can be parsed, log a warning and leave the string as an "unknown" key (do not raise — migration must be robust).

### 2.2 `bec_voltage_v` (scalar float) → BEC voltage toggle

Snap to nearest standard voltage (tolerance ±0.1 V), set matching `bec_voltage_*` to `True`.

### 2.3 `cells` (legacy single integer) → drop

Remove the key from specs. No replacement.

### 2.4 Standard voltage → field name map

```python
_BEC_VOLTAGE_MAP = {
    5.0:  "bec_voltage_5v",
    5.5:  "bec_voltage_5_5v",
    6.0:  "bec_voltage_6v",
    6.5:  "bec_voltage_6_5v",
    7.4:  "bec_voltage_7_4v",
    8.4:  "bec_voltage_8_4v",
    9.0:  "bec_voltage_9v",
    12.0: "bec_voltage_12v",
}
```

---

## 3. Test Files and Test Names

### 3.1 Backend — Registry / Validation
**File:** `app/tests/test_esc_schema_gh1009.py` (new)

```
TestEscRegistrySchema
  test_esc_seed_has_canonical_field_list
      # Assert DEFAULT_SEED_TYPES['esc'] has exactly the 19 canonical fields and
      # does NOT contain 'cells', 'bec_voltage_v', 'bec_output'.
  test_esc_seed_max_current_a_is_required
      # Assert max_current_a has required=True.
  test_esc_seed_protocol_options_unchanged
      # Assert protocol.options == ["pwm","oneshot","dshot150","dshot300","dshot600"].
  test_validate_specs_accepts_new_esc_fields
      # validate_specs(db, 'esc', {max_current_a:30, bec_voltage_5v:True,
      #   cells_nixx_min:5, cells_nixx_max:12}) → no exception.
  test_validate_specs_rejects_boolean_as_number
      # validate_specs(db, 'esc', {max_current_a:30, bec_voltage_5v:1}) →
      # ValidationError (bec_voltage_5v must be true/false).
  test_validate_specs_rejects_old_bec_output_field
      # bec_output no longer in schema → validate_specs does NOT raise
      # (unknown keys are tolerated), but bec_output does not appear in
      # the type's schema list.
  test_validate_specs_rejects_old_cells_field
      # same tolerance pattern: cells unknown but tolerated.
  test_validate_specs_requires_max_current_a
      # validate_specs(db, 'esc', {}) → ValidationError: max_current_a missing.
  test_esc_labels_are_english
      # All field .label values contain no German words (no "Zellen",
      # "Spannung", "Strom", "Ausgang", "Protokoll").
```

### 3.2 Backend — Alembic Migration (up + down)
**File:** `app/tests/test_migration_gh1009.py` (new)

```
TestMigrationUp
  test_up_replaces_esc_schema_in_db
      # Run upgrade() on an in-memory SQLite DB seeded with the pre-gh1009
      # esc schema_def. After upgrade, component_types.schema where name='esc'
      # contains the canonical 19-field list.
  test_up_removes_cells_bec_voltage_v_bec_output_from_schema
      # Same setup. Post-upgrade: field names do NOT include
      # 'cells', 'bec_voltage_v', 'bec_output'.
  test_up_migrates_bec_output_slash_notation
      # Insert a component with specs={'bec_output': '5V/6V 4A',
      #   'continuous_current_a': 20.0, 'max_current_a': 30.0}.
      # After upgrade, specs contains bec_voltage_5v=True,
      # bec_voltage_6v=True, bec_current_a=4.
      # 'bec_output' is absent.
  test_up_migrates_bec_output_single_voltage
      # '5V / 8A' → bec_voltage_5v=True, bec_current_a=8. No 6V toggle.
  test_up_migrates_bec_output_multi_voltage_german_string
      # '5.0V, 5.5V, 6V einstellbar - 5A' → 5v+5_5v+6v=True, bec_current_a=5.
  test_up_migrates_bec_output_null
      # specs={'bec_output': null} → no bec_voltage_* keys set.
  test_up_migrates_bec_voltage_v_scalar
      # specs={'bec_voltage_v': 6.0} → bec_voltage_6v=True. bec_voltage_v absent.
  test_up_drops_cells_key
      # specs={'cells': 3} → specs does not contain 'cells'.
  test_up_preserves_other_fields
      # specs={'continuous_current_a': 20.0, 'art_no': 'X1'} → both preserved.
  test_up_nonexistent_esc_type_is_noop
      # upgrade() on a blank DB (no esc row) → completes without error.

TestMigrationDown
  test_down_restores_pre_gh1009_schema
      # After upgrade() + downgrade(), the esc schema_def matches the
      # pre-gh1009 field list exactly (same 10 fields as in
      # 1f320603c2cf after its upgrade: max_current_a, cells,
      # bec_voltage_v, bec_current_a, protocol, continuous_current_a,
      # cells_lipo_min, cells_lipo_max, bec_output, art_no).
  test_down_does_not_touch_component_specs
      # Downgrade does NOT reverse spec data migration (data migrations
      # are one-way — spec data is not restored). Only the schema_def
      # row is reverted. Document this explicitly in the test.
```

### 3.3 Backend — COTS Re-import Idempotency
**File:** `app/tests/test_cots_esc_gh1009.py` (new)

```
TestCotsEscGh1009
  test_avicon_20a_import_sets_bec_voltage_toggles
      # Import the new dpower.json AVICON 20A record (which now has
      # bec_voltage_5v=True, bec_voltage_6v=True, bec_current_a=4,
      # cells_nixx_min=5, cells_nixx_max=12).
      # Assert all five fields land in specs.
  test_avicon_20a_reimport_is_idempotent
      # Import twice; assert updated=0, skipped=1 on second run.
  test_avicon_opto_no_bec_toggles
      # Antares 85A OPTO has no BEC: none of the bec_voltage_* keys
      # are True; bec_current_a absent.
  test_antares_sbec_multi_voltage
      # Antares 45A SBEC 5A (now with bec_voltage_5v+5_5v+6v=True,
      # bec_current_a=5). Assert three toggles true.
  test_avicon_pro_hv_only_5v
      # AVICON PRO 65A HV: only bec_voltage_5v=True (parsed from "5V / 8A").
  test_esc_record_bbox_preserved
      # AVICON 20A: bbox_x_mm=60, bbox_y_mm=25, bbox_z_mm=10 imported.
```

### 3.4 Frontend — Edit Component Dialog
**File:** `frontend/__tests__/ComponentEditDialogEsc.test.tsx` (new)

```
ComponentEditDialog — ESC type (gh-1009)
  renders bec_voltage_5v and bec_voltage_6v as checkboxes
  renders cells_nixx_min and cells_nixx_max as number inputs
  renders cells_liion_min and cells_liion_max as number inputs
  does NOT render bec_output field
  does NOT render cells field
  does NOT render bec_voltage_v field
  bec_voltage_5v checkbox defaults to false
  checking bec_voltage_5v submits bec_voltage_5v=true in specs
  unchecking bec_voltage_6v submits bec_voltage_6v=false in specs
  renders bbox_x_mm bbox_y_mm bbox_z_mm as L / W / H number inputs
  bbox fields are present alongside spec fields in the dialog
  renders max_current_a as required (star suffix in label)
  renders protocol as a select with pwm/oneshot/dshot* options
  renders art_no as text input with label "Article No."
  labels are in English (no German text rendered)
```

> `bbox_x/y/z_mm` are component-level fields, not in the ESC schema_def.
> The dialog currently hard-codes `bbox_x_mm: null` on save (line 171 of
> `ComponentEditDialog.tsx`). The test must verify that L/W/H fields are
> rendered and their values flow through to the save payload. This requires
> a UI change (see §5).

---

## 4. Code Edit Locations

### 4.1 `app/services/component_type_service.py`

**Symbol:** `DEFAULT_SEED_TYPES` — the `esc` entry (lines 432–459).

Replace the entire `esc` dict in `DEFAULT_SEED_TYPES` with the 19-field canonical schema (English labels, new NiXX/LiIon cell fields, 8 bec_voltage_* booleans).

The comment at line 282 must be updated to reference the new migration revision ID.

### 4.2 `alembic/versions/<new-rev>_gh1009_esc_schema_enrichment.py` (new file)

Create with:
- `down_revision = "1f320603c2cf"` (the current head)
- `upgrade()`:
  1. Read `component_types.schema` where `name = 'esc'`.
  2. Build the new 19-field schema list (canonical English, same as DEFAULT_SEED_TYPES esc entry).
  3. `UPDATE component_types SET schema = :new_schema WHERE name = 'esc'`.
  4. Fetch all `components` rows where `component_type = 'esc'`.
  5. For each row, call `_migrate_esc_specs(specs: dict) -> dict`:
     - Parse `bec_output` (if present) → set bec_voltage_* toggles + bec_current_a.
     - Parse `bec_voltage_v` (if present) → set matching bec_voltage_* toggle.
     - Drop `cells`.
     - Drop `bec_output` and `bec_voltage_v`.
     - Return cleaned dict.
  6. `UPDATE components SET specs = :migrated WHERE id = :id` for changed rows.
- `downgrade()`:
  1. Restore the pre-gh1009 10-field ESC schema (the exact field list that `1f320603c2cf` left in place).
  2. Do NOT reverse component spec data (one-way data migration — document with comment).

**Helper functions inside the migration file:**

```python
_BEC_VOLTAGE_MAP = {5.0: "bec_voltage_5v", 5.5: "bec_voltage_5_5v", ...}
_STD_VOLTAGES = sorted(_BEC_VOLTAGE_MAP.keys())  # [5.0, 5.5, ..., 12.0]

def _snap_voltage(v: float) -> str | None:
    """Snap v to the nearest standard BEC voltage (±0.1 V), return field name."""
    ...

def _parse_bec_output(raw: str) -> dict[str, bool | float]:
    """Parse free-text bec_output string → dict of bec_voltage_* + bec_current_a."""
    ...

def _migrate_esc_specs(specs: dict) -> dict:
    """Transform a single ESC component's specs dict in-place."""
    ...
```

### 4.3 `data/cots/dpower.json`

Update all 18 ESC entries. For each:
- Remove `bec_output` key.
- Add `bec_voltage_5v`, `bec_voltage_6v` (and/or others as applicable), `bec_current_a`.
- Add `cells_nixx_min`, `cells_nixx_max` where known from source (AVICON 20-100A: 5–12; AVICON PRO HV: not specified → omit; Antares: not specified → omit; OPTO: no BEC).
- Do NOT add `cells` or `bec_voltage_v`.

Specific per-model mapping (all source voltages from dpower.json bec_output):

| Model | bec_voltage_* toggles | bec_current_a | cells_nixx_min | cells_nixx_max |
|---|---|---|---|---|
| AVICON 20A–50A | 5v=T, 6v=T | 4 | 5 | 12 |
| AVICON 60A–100A | 5v=T, 6v=T | 8 | 5 | 12 |
| AVICON PRO 65/125/130A HV | 5v=T | 8 | omit | omit |
| Antares 6A BEC | 5v=T | 1 | omit | omit |
| Antares 12A BEC | 5v=T | 1 | omit | omit |
| Antares 25A BEC | 5v=T | 2 | omit | omit |
| Antares 45A SBEC 5A | 5v=T, 5_5v=T, 6v=T | 5 | omit | omit |
| Antares 65A SBEC 5A | 5v=T, 5_5v=T, 6v=T | 5 | omit | omit |
| Antares 85A SBEC 5A | 5v=T, 5_5v=T, 6v=T | 5 | omit | omit |
| Antares 85A OPTO | (none) | omit | omit | omit |
| Antares 90A OPTO | (none) | omit | omit | omit |
| Antares 150A OPTO | (none) | omit | omit | omit |

### 4.4 `frontend/components/workbench/ComponentEditDialog.tsx`

Two changes:

**Change A — Expose bbox fields:**

Add state for `bboxX`, `bboxY`, `bboxZ` (initialised from `component.bbox_x/y/z_mm`). Add three number inputs in the form body between the Mass row and the Manufacturer field, grouped as "Dimensions":

```tsx
{/* Dimensions L × W × H */}
<div className="flex gap-2">
  <div className="flex min-w-0 flex-1 flex-col gap-1">
    <label htmlFor="ce-bbox-x" className="text-[11px] text-muted-foreground">Length (mm)</label>
    <input id="ce-bbox-x" type="number" value={bboxX} onChange={(e) => setBboxX(e.target.value)}
      className="w-full rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground" />
  </div>
  <div className="flex min-w-0 flex-1 flex-col gap-1">
    <label htmlFor="ce-bbox-y" className="text-[11px] text-muted-foreground">Width (mm)</label>
    <input id="ce-bbox-y" type="number" value={bboxY} onChange={(e) => setBboxY(e.target.value)}
      className="w-full rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground" />
  </div>
  <div className="flex min-w-0 flex-1 flex-col gap-1">
    <label htmlFor="ce-bbox-z" className="text-[11px] text-muted-foreground">Height (mm)</label>
    <input id="ce-bbox-z" type="number" value={bboxZ} onChange={(e) => setBboxZ(e.target.value)}
      className="w-full rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground" />
  </div>
</div>
```

**Change B — Pass bbox values to save payload:**

In `handleSave` → `data` object, replace the three `null` literals:

```typescript
// Before (lines 170–172):
bbox_x_mm: null,
bbox_y_mm: null,
bbox_z_mm: null,

// After:
bbox_x_mm: bboxX ? Number.parseFloat(bboxX) : null,
bbox_y_mm: bboxY ? Number.parseFloat(bboxY) : null,
bbox_z_mm: bboxZ ? Number.parseFloat(bboxZ) : null,
```

No changes to `SpecField` or validation logic — the boolean/enum/number renderers already handle all new field types correctly.

---

## 5. TDD Execution Order

The TDD sequence follows the dependency graph: write failing test → implement → green → next.

```
Step 1  Write test_esc_schema_gh1009.py (all tests)
        → All fail (seed still has old German schema)

Step 2  Update DEFAULT_SEED_TYPES['esc'] in component_type_service.py
        → test_esc_seed_* pass; validate_specs tests pass via seed_default_types fixture

Step 3  Write test_migration_gh1009.py
        → All fail (migration file does not exist yet)

Step 4  Create alembic/versions/<rev>_gh1009_esc_schema_enrichment.py
        with _migrate_esc_specs helpers and upgrade/downgrade
        → test_migration_* pass

Step 5  Update data/cots/dpower.json AVICON/Antares ESC entries
        (remove bec_output, add bec_voltage_* + cells_nixx_*)

Step 6  Write test_cots_esc_gh1009.py
        → Tests pass immediately since JSON is already updated

Step 7  Write frontend/__tests__/ComponentEditDialogEsc.test.tsx
        → bbox tests fail; bec_voltage checkbox tests pass (schema
          already drives SpecField which handles boolean)

Step 8  Update ComponentEditDialog.tsx (add bbox state + inputs + save)
        → All frontend tests green

Step 9  Run full suite: poetry run pytest -x; cd frontend && npm run test:unit
        → Confirm coverage >80% for touched modules
```

---

## 6. Migration Revision Naming

```
alembic revision --message "gh_1009_esc_schema_enrichment_english_bec_toggles"
```

Expected revision ID: auto-generated 12-char hex. The `down_revision` must be `"1f320603c2cf"`.

---

## 7. Pre-gh1009 ESC Schema (for downgrade target)

After `1f320603c2cf` ran, the ESC schema_def had exactly these 10 fields:

```json
[
  {"name": "max_current_a",      "label": "Max Strom (kurz)",  "type": "number", "unit": "A", "required": true},
  {"name": "cells",              "label": "Zellen (S)",         "type": "number"},
  {"name": "bec_voltage_v",      "label": "BEC Spannung",       "type": "number", "unit": "V"},
  {"name": "bec_current_a",      "label": "BEC Strom",          "type": "number", "unit": "A"},
  {"name": "protocol",           "label": "Protokoll",          "type": "enum",
   "options": ["pwm","oneshot","dshot150","dshot300","dshot600"]},
  {"name": "continuous_current_a","label": "Dauerstrom",        "type": "number", "unit": "A"},
  {"name": "cells_lipo_min",     "label": "LiPo Zellen min",    "type": "number"},
  {"name": "cells_lipo_max",     "label": "LiPo Zellen max",    "type": "number"},
  {"name": "bec_output",         "label": "BEC Ausgang",        "type": "string"},
  {"name": "art_no",             "label": "Art.-Nr.",           "type": "string"}
]
```

This is the exact target for `downgrade()`.

---

## 8. Coverage Notes

| File | Untested paths requiring explicit test |
|---|---|
| `_snap_voltage` | voltage outside all ±0.1 bands (→ None / log warning) |
| `_parse_bec_output` | null input; no voltage tokens; no current token |
| `_migrate_esc_specs` | spec with neither bec_output nor bec_voltage_v; spec with both |
| `ComponentEditDialog.tsx` | bbox values round-trip through save payload |

Backend coverage target for migration helpers: 100% (all branches). The helpers are pure functions — test them directly in `test_migration_gh1009.py` without needing Alembic runner:

```python
from alembic.versions.<rev>_gh1009... import _snap_voltage, _parse_bec_output, _migrate_esc_specs
```

---

## 9. Files Changed Summary

| File | Action |
|---|---|
| `app/services/component_type_service.py` | Edit `DEFAULT_SEED_TYPES['esc']` |
| `alembic/versions/<rev>_gh1009_esc_*.py` | **Create** |
| `data/cots/dpower.json` | Edit 18 ESC entries |
| `frontend/components/workbench/ComponentEditDialog.tsx` | Edit (bbox state + inputs + save) |
| `app/tests/test_esc_schema_gh1009.py` | **Create** |
| `app/tests/test_migration_gh1009.py` | **Create** |
| `app/tests/test_cots_esc_gh1009.py` | **Create** |
| `frontend/__tests__/ComponentEditDialogEsc.test.tsx` | **Create** |
