# ESC Component Model Enrichment + English Translation

**Date:** 2026-06-16
**Type:** Feature / enhancement (`enhancement`)
**Status:** Design approved, ready for ticket

## Problem

The ESC (Electronic Speed Controller) component type accreted an
overlapping, partly redundant field set across successive D-Power /
AVICON imports, and all field labels are in German. Discovered while
importing AVICON ESCs:

1. **Cell count** is incomplete — only `cells_lipo_min/max` exist.
   There is no NiXX (NiCd/NiMH) min/max, even though AVICON specs list
   both chemistries (e.g. AVICON 20A: LiPo 2–4, NiXX 5–12). A legacy
   single `cells` field also lingers.
2. **BEC voltage** is unstructured — stored either as a single scalar
   `bec_voltage_v` or crammed into a free-text `bec_output` string
   (`"5V/6V 4A"`). It cannot represent a selectable/range BEC output.
3. **Dimensions** L×W×H were thought to be missing. They are not: every
   component already has `bbox_x_mm / bbox_y_mm / bbox_z_mm`, and the
   AVICON import already populated them (`60×25×10`). The real gap is
   that they are **not surfaced in the Edit Component dialog**.
4. **Labels are German** (Dauerstrom, Zellen, Spannung, …) and should
   be English.

## Nature of the change

ESC is stored as a generic `components` row (`component_type='esc'`)
with all type-specific fields in a JSON `specs` column, validated
against an editable **component-type registry**
(`app/services/component_type_service.py` seed +
`component_types` DB table). This change is therefore a **registry
schema cleanup plus a data migration** — **no change** to the
`components` SQLAlchemy table.

## Canonical ESC `specs` schema (English labels)

| Field | Label | Type | Unit | Notes |
|---|---|---|---|---|
| `continuous_current_a` | Continuous Current | number | A | primary current rating |
| `max_current_a` | Burst Current | number | A | was "Max Strom (kurz)" |
| `cells_lipo_min` / `cells_lipo_max` | LiPo Cells Min / Max | number | S | |
| `cells_nixx_min` / `cells_nixx_max` | NiXX Cells Min / Max | number | cells | **new** |
| `cells_liion_min` / `cells_liion_max` | Li-Ion/LiHV Cells Min / Max | number | S | **new** |
| `bec_voltage_min_v` / `bec_voltage_max_v` | BEC Voltage Min / Max | number | V | replaces scalar + free string |
| `bec_current_a` | BEC Current | number | A | |
| `protocol` | Protocol | enum | — | options unchanged |
| `art_no` | Article No. | string | — | was "Art.-Nr." |

**Removed & migrated:** `cells` (legacy single), `bec_voltage_v`
(scalar), `bec_output` (free string).

> **Note (design decision):** BEC voltage is modeled as a **min/max
> range**, not a discrete selectable set. AVICON's `"5V/6V"` is
> physically a discrete switch (5V *or* 6V), so for AVICON
> `min=5, max=6`. This was an explicit choice over a multi-value list.

## Dimensions

Reuse existing `bbox_x_mm` (length), `bbox_y_mm` (width),
`bbox_z_mm` (height). **No new fields.** Frontend surfaces these three
in the Edit Component dialog with English L/W/H labels. AVICON data
already populates them.

## Data migration (Alembic + re-import)

1. Rewrite the `esc` type schema in both the seed
   (`DEFAULT_SEED_TYPES`) and the `component_types` DB row to the
   canonical set above.
2. Migrate existing component `specs`:
   - `bec_output "5V/6V 4A"` → `bec_voltage_min_v=5`,
     `bec_voltage_max_v=6`, `bec_current_a=4` (parse defensively;
     leave unparseable strings untouched and log).
   - `bec_voltage_v=x` → `bec_voltage_min_v = bec_voltage_max_v = x`.
   - drop legacy `cells`.
3. Update `data/cots/dpower.json` AVICON entries to add
   `cells_nixx_min/max` and structured `bec_voltage_min/max_v` +
   `bec_current_a`, then re-import via the existing COTS import path.

## Acceptance criteria

- [ ] `esc` registry schema exposes the canonical fields above with
      English labels; `cells`, `bec_voltage_v`, `bec_output` removed.
- [ ] Alembic migration updates seed + DB row and migrates existing
      ESC specs (BEC parse, scalar→range, drop `cells`); downgrade
      restores the prior schema.
- [ ] `data/cots/dpower.json` AVICON ESCs carry NiXX cell range and
      structured BEC voltage min/max + current; re-import is
      idempotent and yields the new fields.
- [ ] Edit Component dialog renders `bbox_x/y/z_mm` as L/W/H plus the
      new spec fields, all English-labeled.
- [ ] Tests: registry validation (new fields accepted, removed fields
      rejected), migration up/down on a seeded DB, re-import
      idempotency, frontend dialog field rendering.
- [ ] Coverage stays > 80%.

## Out of scope

- SQLAlchemy column changes to the `components` table.
- MCP tooling for components (none exists today).
- Any non-ESC component type.
- Discrete multi-value BEC representation (range chosen instead).
