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
| `bec_voltage_5v` | BEC 5.0 V | boolean | — | selectable BEC output |
| `bec_voltage_5_5v` | BEC 5.5 V | boolean | — | selectable BEC output |
| `bec_voltage_6v` | BEC 6.0 V | boolean | — | selectable BEC output |
| `bec_voltage_6_5v` | BEC 6.5 V | boolean | — | selectable BEC output |
| `bec_voltage_7_4v` | BEC 7.4 V | boolean | — | selectable BEC output |
| `bec_voltage_8_4v` | BEC 8.4 V | boolean | — | selectable BEC output |
| `bec_voltage_9v` | BEC 9.0 V | boolean | — | selectable BEC output |
| `bec_voltage_12v` | BEC 12.0 V | boolean | — | selectable BEC output |
| `bec_current_a` | BEC Current | number | A | |
| `protocol` | Protocol | enum | — | options unchanged |
| `art_no` | Article No. | string | — | was "Art.-Nr." |

**Removed & migrated:** `cells` (legacy single), `bec_voltage_v`
(scalar), `bec_output` (free string).

> **Note (design decision):** BEC voltage is modeled as a **discrete
> set of selectable standard voltages**, each a `boolean` toggle
> (true = the ESC can output that voltage). This matches how real
> BECs expose jumper/app-selectable steps. AVICON's `"5V/6V"` →
> `bec_voltage_5v=true`, `bec_voltage_6v=true`, rest false.
>
> The standard set (5–12 V) is grounded in the `rc-aircraft-designer`
> RC-Network material: the 5/6 V receiver tier (`rcn-bec`) and the
> 6 V→8.4 V HV-servo tier (`rcn-servo`), extended with standard
> programmable-UBEC steps up to 12 V:
> **5.0, 5.5, 6.0, 6.5, 7.4, 8.4, 9.0, 12.0 V**.
> (7.2 V and 10/11 V deliberately excluded — pack-nominal /
> continuous-adjust only, not standard discrete toggles.)

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
   - `bec_output "5V/6V 4A"` → set the matching `bec_voltage_*`
     toggles true (`bec_voltage_5v`, `bec_voltage_6v`) +
     `bec_current_a=4` (parse defensively; snap each parsed voltage to
     the nearest standard value, leave unparseable strings untouched
     and log).
   - `bec_voltage_v=x` → set the matching standard `bec_voltage_*`
     toggle true.
   - drop legacy `cells`.
3. Update `data/cots/dpower.json` AVICON entries to add
   `cells_nixx_min/max`, the selected `bec_voltage_*` boolean toggles
   (e.g. `bec_voltage_5v=true`, `bec_voltage_6v=true`), and
   `bec_current_a`, then re-import via the existing COTS import path.

## Acceptance criteria

- [ ] `esc` registry schema exposes the canonical fields above with
      English labels; `cells`, `bec_voltage_v`, `bec_output` removed.
- [ ] Alembic migration updates seed + DB row and migrates existing
      ESC specs (BEC parse, scalar→range, drop `cells`); downgrade
      restores the prior schema.
- [ ] `data/cots/dpower.json` AVICON ESCs carry NiXX cell range, the
      correct `bec_voltage_*` toggles (5 V + 6 V true), and
      `bec_current_a`; re-import is idempotent and yields the new
      fields.
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
- Continuous-adjust / arbitrary BEC voltages (only the standard
  discrete set 5.0–12.0 V is offered as toggles).
