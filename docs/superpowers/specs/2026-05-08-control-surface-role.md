# Design Spec: Standardized Control Surface Role Dropdown (#439)

**Epic:** #417 — Operating Point Simulation
**Date:** 2026-05-08

## Problem

Control surface names are free-form strings. The OP generator uses
substring matching (`"elevator" in name.lower()`) to detect available
controls. This is brittle (non-English names silently fail) and ignores
flaps entirely — no auto-OP uses flap deployment for takeoff/landing.

### Current flow

1. `TedEditDialog` — free-text `name` input, no validation
2. Schema `TrailingEdgeDeviceDetailSchema` — `name: Optional[str]`
3. DB `WingXSecTrailingEdgeDeviceModel` — `name` column (String, nullable)
4. Converter `_control_surface_from_ted()` — passes `name` through to ASB
5. `_detect_control_capabilities()` — substring match on ASB control names
6. `_pick_control_name()` — substring token matching for pitch/roll/yaw

## Design

### ControlSurfaceRole enum

```python
class ControlSurfaceRole(str, Enum):
    ELEVATOR = "elevator"
    AILERON = "aileron"
    RUDDER = "rudder"
    ELEVON = "elevon"        # combined pitch + roll
    STABILATOR = "stabilator" # all-moving horizontal stabilizer
    FLAP = "flap"            # high-lift device
    SPOILER = "spoiler"      # future: drag/roll
    OTHER = "other"          # user-defined, not auto-trimmed
```

### Schema changes

`TrailingEdgeDeviceDetailSchema`:
- Add `role: ControlSurfaceRole` (required, dropdown in UI)
- Add `label: str | None = None` (optional user display name)
- Keep `name: str` as computed: `label or role.value` (backwards compat)

### Database migration

- Add `role` column (String, NOT NULL, default `"other"`) to
  `wing_xsec_trailing_edge_devices`
- Add `label` column (String, nullable)
- Data migration: infer `role` from existing `name` using substring
  matching, set `label = name`

### Backend changes

- `_detect_control_capabilities()` → rewrite to use `role` field
  propagated through ASB control surface metadata
- `_pick_control_name()` → match by role enum, not substring
- Add flap support to OP generator:
  - `takeoff_climb` → deploy flaps
  - `approach_landing` → deploy flaps
  - New OP: `stall_with_flaps`
- `_control_surface_from_ted()` → pass role through to ASB

### Frontend changes

- `TedEditDialog`: role dropdown (required) + optional label text field
- Tree node chips: show role + label
- Validation: warn if no elevator role on any wing

## Acceptance Criteria

1. User selects control surface role from dropdown when adding a TED
2. Optional custom label preserved for display
3. OP generator uses `role` field — no more substring matching
4. Flaps deployed in takeoff_climb and approach_landing OPs
5. Existing data migrated correctly (no broken configs)
6. Non-English users get correct auto-trim without naming constraints
