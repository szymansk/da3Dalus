# Control Surface Role Enum Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace free-form control surface names with a standardized `ControlSurfaceRole` enum, enabling role-based detection and flap support in the OP generator.

**Architecture:** Add `role` and `label` columns to the TED model/schema, propagate role through the converter to ASB control surfaces (encoded in the name), rewrite `_detect_control_capabilities()` and `_pick_control_name()` to decode role from the name, add flap deployment logic to takeoff/landing OPs, and update the frontend `TedEditDialog` with a role dropdown.

**Tech Stack:** Python 3.11, Pydantic v2, SQLAlchemy, Alembic, FastAPI, React 19, Next.js 16, Tailwind CSS

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `app/schemas/aeroplaneschema.py` | Add `ControlSurfaceRole` enum, `role`/`label` fields to TED schemas |
| Modify | `app/models/aeroplanemodel.py` | Add `role`/`label` columns to TED model |
| Create | `alembic/versions/a1b2c3d4e5f6_add_role_label_to_ted.py` | Migration + data backfill |
| Modify | `app/converters/model_schema_converters.py` | Encode role in control surface name |
| Modify | `app/services/operating_point_generator_service.py` | Role-based detection, flap deployment |
| Modify | `app/services/wing_service.py` | Handle role/label in TED patch |
| Create | `app/tests/test_control_surface_role.py` | Tests for enum, schema, detection, flaps |
| Modify | `frontend/components/workbench/TedEditDialog.tsx` | Role dropdown + label field |
| Modify | `frontend/components/workbench/AeroplaneTree.tsx` | Role-based TED display |
| Create | `frontend/__tests__/TedEditDialog.test.tsx` | Frontend tests for role dropdown |

---

### Task 1: ControlSurfaceRole Enum and Schema Fields

**Files:**
- Modify: `app/schemas/aeroplaneschema.py`
- Create: `app/tests/test_control_surface_role.py`

- [ ] **Step 1: Write failing tests for enum and schema**

```python
# app/tests/test_control_surface_role.py
import pytest
from app.schemas.aeroplaneschema import (
    ControlSurfaceRole,
    TrailingEdgeDeviceDetailSchema,
    TrailingEdgeDevicePatchSchema,
)


class TestControlSurfaceRole:
    def test_enum_values(self):
        assert ControlSurfaceRole.ELEVATOR == "elevator"
        assert ControlSurfaceRole.FLAP == "flap"
        assert ControlSurfaceRole.OTHER == "other"

    def test_all_roles_present(self):
        expected = {"elevator", "aileron", "rudder", "elevon", "stabilator", "flap", "spoiler", "other"}
        assert {r.value for r in ControlSurfaceRole} == expected


class TestTedSchemaRoleField:
    def test_role_defaults_to_other(self):
        ted = TrailingEdgeDeviceDetailSchema()
        assert ted.role == ControlSurfaceRole.OTHER

    def test_role_set_explicitly(self):
        ted = TrailingEdgeDeviceDetailSchema(role="elevator")
        assert ted.role == ControlSurfaceRole.ELEVATOR

    def test_label_optional(self):
        ted = TrailingEdgeDeviceDetailSchema(role="aileron", label="Left Aileron")
        assert ted.label == "Left Aileron"

    def test_name_computed_from_role_when_no_label(self):
        ted = TrailingEdgeDeviceDetailSchema(role="elevator")
        assert ted.name == "elevator"

    def test_name_computed_from_label_when_present(self):
        ted = TrailingEdgeDeviceDetailSchema(role="aileron", label="Left Aileron")
        assert ted.name == "Left Aileron"

    def test_name_field_still_accepted_for_backwards_compat(self):
        ted = TrailingEdgeDeviceDetailSchema(name="Höhenruder", role="elevator")
        assert ted.role == ControlSurfaceRole.ELEVATOR

    def test_invalid_role_rejected(self):
        with pytest.raises(Exception):
            TrailingEdgeDeviceDetailSchema(role="invalid_role")


class TestTedPatchSchemaRoleField:
    def test_patch_with_role_only(self):
        patch = TrailingEdgeDevicePatchSchema(role="flap")
        assert patch.role == ControlSurfaceRole.FLAP

    def test_patch_with_label_only(self):
        patch = TrailingEdgeDevicePatchSchema(label="Inboard Flap")
        assert patch.label == "Inboard Flap"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest app/tests/test_control_surface_role.py -v`
Expected: FAIL — `ControlSurfaceRole` not defined

- [ ] **Step 3: Add enum and schema fields**

In `app/schemas/aeroplaneschema.py`, add the enum before `ControlSurfaceSchema`:

```python
class ControlSurfaceRole(str, Enum):
    ELEVATOR = "elevator"
    AILERON = "aileron"
    RUDDER = "rudder"
    ELEVON = "elevon"
    STABILATOR = "stabilator"
    FLAP = "flap"
    SPOILER = "spoiler"
    OTHER = "other"
```

Add `role` and `label` fields to `TrailingEdgeDeviceDetailSchema` (after `name`):

```python
    role: ControlSurfaceRole = Field(
        ControlSurfaceRole.OTHER,
        description="Standardized control surface role for auto-trim detection",
    )
    label: Optional[str] = Field(None, description="Optional user-defined display name")
```

Add a computed `name` validator that sets `name` from `label or role.value` when not explicitly provided:

```python
    @model_validator(mode="after")
    def _compute_name_from_role(self):
        if self.name is None:
            self.name = self.label if self.label else self.role.value
        return self
```

Add `role` and `label` to `TrailingEdgeDevicePatchSchema`:

```python
    role: Optional[ControlSurfaceRole] = Field(None, description="Control surface role")
    label: Optional[str] = Field(None, description="Optional display name")
```

Add `self.role` and `self.label` to the non-empty patch validator's field list.

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_control_surface_role.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `poetry run pytest -m "not slow" --tb=short -q`
Expected: All existing tests pass (role defaults to "other", name computed from role)

- [ ] **Step 6: Commit**

```bash
git add app/schemas/aeroplaneschema.py app/tests/test_control_surface_role.py
git commit -m "feat(gh-439): add ControlSurfaceRole enum and schema fields"
```

---

### Task 2: Database Migration

**Files:**
- Modify: `app/models/aeroplanemodel.py`
- Create: `alembic/versions/*_add_role_label_to_ted.py`

- [ ] **Step 1: Add columns to ORM model**

In `app/models/aeroplanemodel.py`, add to `WingXSecTrailingEdgeDeviceModel` after the `name` column:

```python
    role = Column(String, nullable=False, server_default="other")
    label = Column(String, nullable=True)
```

- [ ] **Step 2: Generate Alembic migration**

Run: `poetry run alembic revision --autogenerate -m "add role and label to ted"`

- [ ] **Step 3: Add data migration to the generated file**

Edit the generated migration to add a data backfill step after `op.add_column`. The backfill infers `role` from existing `name` values using the same substring logic the OP generator currently uses, and sets `label = name`:

```python
def _infer_role(name):
    if not name:
        return "other"
    n = name.strip().lower()
    if "stabilator" in n:
        return "stabilator"
    if "elevon" in n:
        return "elevon"
    if "elevator" in n:
        return "elevator"
    if "aileron" in n:
        return "aileron"
    if "rudder" in n:
        return "rudder"
    if "flap" in n:
        return "flap"
    if "spoiler" in n:
        return "spoiler"
    return "other"


def upgrade():
    op.add_column("wing_xsec_trailing_edge_devices", sa.Column("role", sa.String(), server_default="other", nullable=False))
    op.add_column("wing_xsec_trailing_edge_devices", sa.Column("label", sa.String(), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, name FROM wing_xsec_trailing_edge_devices")).fetchall()
    for row in rows:
        role = _infer_role(row.name)
        conn.execute(
            sa.text("UPDATE wing_xsec_trailing_edge_devices SET role = :role, label = :label WHERE id = :id"),
            {"role": role, "label": row.name, "id": row.id},
        )
```

- [ ] **Step 4: Run migration**

Run: `poetry run alembic upgrade head`
Expected: Migration applies without errors

- [ ] **Step 5: Verify ORM round-trip**

Run: `poetry run pytest -m "not slow" --tb=short -q`
Expected: All tests pass — ORM hydration picks up `role` (defaults to "other") and `label`

- [ ] **Step 6: Commit**

```bash
git add app/models/aeroplanemodel.py alembic/versions/
git commit -m "feat(gh-439): add role/label columns to TED with data migration"
```

---

### Task 3: Converter — Encode Role in Control Surface Name

**Files:**
- Modify: `app/converters/model_schema_converters.py`
- Modify: `app/tests/test_control_surface_role.py`

The ASB `ControlSurface` object has only a `name` field — no metadata slot. We encode the role by prefixing the name: `"[role]display_name"`. The OP generator will decode this.

- [ ] **Step 1: Write failing tests**

Append to `app/tests/test_control_surface_role.py`:

```python
from app.converters.model_schema_converters import _control_surface_from_ted


class TestConverterRoleEncoding:
    def test_role_encoded_in_name(self):
        ted = TrailingEdgeDeviceDetailSchema(role="elevator")
        cs = _control_surface_from_ted(ted)
        assert cs.name == "[elevator]elevator"

    def test_role_with_label_encoded(self):
        ted = TrailingEdgeDeviceDetailSchema(role="aileron", label="Left Aileron")
        cs = _control_surface_from_ted(ted)
        assert cs.name == "[aileron]Left Aileron"

    def test_other_role_uses_name(self):
        ted = TrailingEdgeDeviceDetailSchema(role="other", name="Custom Thing")
        cs = _control_surface_from_ted(ted)
        assert cs.name == "[other]Custom Thing"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest app/tests/test_control_surface_role.py::TestConverterRoleEncoding -v`
Expected: FAIL — name is not prefixed with role

- [ ] **Step 3: Update converter**

In `app/converters/model_schema_converters.py`, modify `_control_surface_from_ted()`:

Change the name line from:
```python
name = ted.name or (fallback.name if fallback else "Control Surface")
```

To:
```python
display_name = ted.name or (fallback.name if fallback else "Control Surface")
role = ted.role.value if hasattr(ted, "role") and ted.role else "other"
name = f"[{role}]{display_name}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_control_surface_role.py::TestConverterRoleEncoding -v`
Expected: PASS

- [ ] **Step 5: Run full suite for regressions**

Run: `poetry run pytest -m "not slow" --tb=short -q`
Expected: Some existing tests may fail if they check exact control surface names — fix by updating expected values to include the `[role]` prefix. Tests in `test_operating_point_generator_service_extended.py` that test `_pick_control_name` and `_detect_control_capabilities` will be updated in Task 4.

- [ ] **Step 6: Commit**

```bash
git add app/converters/model_schema_converters.py app/tests/test_control_surface_role.py
git commit -m "feat(gh-439): encode role prefix in ASB control surface name"
```

---

### Task 4: Rewrite OP Generator Detection and Add Flap Support

**Files:**
- Modify: `app/services/operating_point_generator_service.py`
- Modify: `app/tests/test_control_surface_role.py`

- [ ] **Step 1: Write failing tests for role-based detection**

Append to `app/tests/test_control_surface_role.py`:

```python
from unittest.mock import MagicMock
from app.services.operating_point_generator_service import (
    _detect_control_capabilities,
    _pick_control_name,
)


def _mock_airplane_with_controls(names: list[str]):
    airplane = MagicMock()
    xsec = MagicMock()
    controls = []
    for n in names:
        cs = MagicMock()
        cs.name = n
        controls.append(cs)
    xsec.control_surfaces = controls
    wing = MagicMock()
    wing.xsecs = [xsec]
    airplane.wings = [wing]
    return airplane


class TestRoleBasedDetection:
    def test_detect_elevator_by_role(self):
        airplane = _mock_airplane_with_controls(["[elevator]Höhenruder"])
        caps = _detect_control_capabilities(airplane)
        assert caps["has_pitch_control"] is True

    def test_detect_aileron_by_role(self):
        airplane = _mock_airplane_with_controls(["[aileron]Querruder"])
        caps = _detect_control_capabilities(airplane)
        assert caps["has_roll_control"] is True

    def test_detect_rudder_by_role(self):
        airplane = _mock_airplane_with_controls(["[rudder]Seitenruder"])
        caps = _detect_control_capabilities(airplane)
        assert caps["has_yaw_control"] is True

    def test_detect_flap_by_role(self):
        airplane = _mock_airplane_with_controls(["[flap]Landeklappe"])
        caps = _detect_control_capabilities(airplane)
        assert caps["has_flap"] is True

    def test_no_flap_when_none_present(self):
        airplane = _mock_airplane_with_controls(["[elevator]Elevator"])
        caps = _detect_control_capabilities(airplane)
        assert caps["has_flap"] is False

    def test_elevon_detected_as_both_pitch_and_roll(self):
        airplane = _mock_airplane_with_controls(["[elevon]Elevon"])
        caps = _detect_control_capabilities(airplane)
        assert caps["has_pitch_control"] is True
        assert caps["has_roll_control"] is True

    def test_other_role_not_detected_as_control(self):
        airplane = _mock_airplane_with_controls(["[other]Custom"])
        caps = _detect_control_capabilities(airplane)
        assert caps["has_pitch_control"] is False
        assert caps["has_roll_control"] is False
        assert caps["has_yaw_control"] is False
        assert caps["has_flap"] is False

    def test_fallback_to_substring_for_untagged_names(self):
        airplane = _mock_airplane_with_controls(["elevator"])
        caps = _detect_control_capabilities(airplane)
        assert caps["has_pitch_control"] is True


class TestRoleBasedPickControl:
    def test_pick_by_role_tag(self):
        result = _pick_control_name(
            ["[aileron]Left Aileron", "[elevator]Höhenruder"],
            roles={"elevator"},
        )
        assert result == "[elevator]Höhenruder"

    def test_pick_flap(self):
        result = _pick_control_name(
            ["[elevator]Elevator", "[flap]Inboard Flap"],
            roles={"flap"},
        )
        assert result == "[flap]Inboard Flap"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest app/tests/test_control_surface_role.py::TestRoleBasedDetection -v`
Expected: FAIL

- [ ] **Step 3: Add role parsing helper**

In `app/services/operating_point_generator_service.py`, add a helper to extract role from encoded names:

```python
import re

_ROLE_TAG_RE = re.compile(r"^\[(\w+)\](.*)$")

PITCH_ROLES = {"elevator", "stabilator", "elevon"}
ROLL_ROLES = {"aileron", "elevon"}
YAW_ROLES = {"rudder"}
FLAP_ROLES = {"flap"}

PITCH_TOKENS = {"elevator", "stabilator", "elevon"}
ROLL_TOKENS = {"aileron", "elevon"}
YAW_TOKENS = {"rudder"}
FLAP_TOKENS = {"flap"}


def _parse_role_tag(name: str) -> tuple[Optional[str], str]:
    m = _ROLE_TAG_RE.match(name)
    if m:
        return m.group(1), m.group(2)
    return None, name
```

- [ ] **Step 4: Rewrite `_detect_control_capabilities()`**

```python
def _detect_control_capabilities(asb_airplane: asb.Airplane) -> dict[str, Any]:
    control_names: list[str] = []
    roles_found: set[str] = set()

    for wing in getattr(asb_airplane, "wings", []) or []:
        for xsec in getattr(wing, "xsecs", []) or []:
            for cs in getattr(xsec, "control_surfaces", []) or []:
                raw_name = str(getattr(cs, "name", "")).strip()
                if not raw_name:
                    continue
                control_names.append(raw_name)
                role, display = _parse_role_tag(raw_name)
                if role:
                    roles_found.add(role)
                else:
                    normalized = raw_name.lower()
                    for token in PITCH_TOKENS | ROLL_TOKENS | YAW_TOKENS | FLAP_TOKENS:
                        if token in normalized:
                            roles_found.add(token)

    return {
        "has_pitch_control": bool(roles_found & PITCH_ROLES),
        "has_roll_control": bool(roles_found & ROLL_ROLES),
        "has_yaw_control": bool(roles_found & YAW_ROLES),
        "has_flap": bool(roles_found & FLAP_ROLES),
        "available_controls": sorted(set(control_names)),
    }
```

- [ ] **Step 5: Rewrite `_pick_control_name()`**

Change signature to accept `roles` as keyword argument alongside existing `tokens` for backwards compat:

```python
def _pick_control_name(
    available_controls: list[str],
    tokens: Optional[set[str]] = None,
    roles: Optional[set[str]] = None,
) -> Optional[str]:
    target_roles = roles or tokens or set()
    for control_name in available_controls:
        role, display = _parse_role_tag(control_name)
        if role and role in target_roles:
            return control_name
    if tokens:
        for control_name in available_controls:
            normalized = control_name.strip().lower()
            if any(token in normalized for token in tokens):
                return control_name
    return None
```

- [ ] **Step 6: Update callers in `_solve_trim_candidate_with_opti()`**

Change the three `_pick_control_name` calls (around line 341-343) to use `roles=`:

```python
pitch_name = _pick_control_name(available_controls, roles=PITCH_ROLES)
yaw_name = _pick_control_name(available_controls, roles=YAW_ROLES)
roll_name = _pick_control_name(available_controls, roles=ROLL_ROLES)
```

- [ ] **Step 7: Add flap deployment to target definitions**

In `_build_target_definitions()`, add a `"flap_deflection_deg"` field to takeoff and landing targets:

```python
        {
            "name": "takeoff_climb",
            "config": "takeoff",
            "velocity": takeoff,
            "altitude": altitude,
            "beta_target_deg": 0.0,
            "n_target": 1.0,
            "flap_deflection_deg": 15.0,
        },
```

```python
        {
            "name": "approach_landing",
            "config": "landing",
            "velocity": approach,
            "altitude": altitude,
            "beta_target_deg": 0.0,
            "n_target": 1.0,
            "flap_deflection_deg": 30.0,
        },
```

Add a new OP after approach_landing:

```python
        {
            "name": "stall_with_flaps",
            "config": "landing",
            "velocity": max(2.0, refs["vs_ldg"] * 1.05),
            "altitude": altitude,
            "beta_target_deg": 0.0,
            "n_target": 1.0,
            "flap_deflection_deg": 30.0,
        },
```

- [ ] **Step 8: Apply flap deflection in trim solver**

In `_solve_trim_candidate_with_opti()`, after the pitch/yaw/roll control variable setup, add:

```python
flap_deflection = target.get("flap_deflection_deg")
if flap_deflection is not None:
    flap_name = _pick_control_name(available_controls, roles=FLAP_ROLES)
    if flap_name:
        control_values[flap_name] = float(flap_deflection)
```

- [ ] **Step 9: Run tests**

Run: `poetry run pytest app/tests/test_control_surface_role.py -v`
Expected: PASS

- [ ] **Step 10: Fix any regressions in existing OP generator tests**

Run: `poetry run pytest app/tests/test_operating_point_generator_service_extended.py -v`

Update any tests that check exact `_pick_control_name` behavior to account for the new `roles` parameter. The old `tokens` parameter still works for backwards compat.

- [ ] **Step 11: Run full suite**

Run: `poetry run pytest -m "not slow" --tb=short -q`
Expected: All pass

- [ ] **Step 12: Commit**

```bash
git add app/services/operating_point_generator_service.py app/tests/test_control_surface_role.py
git commit -m "feat(gh-439): role-based control detection and flap deployment in OP generator"
```

---

### Task 5: Update Wing Service for Role/Label Patch

**Files:**
- Modify: `app/services/wing_service.py`
- Modify: `app/tests/test_control_surface_role.py`

- [ ] **Step 1: Write failing test**

Append to `app/tests/test_control_surface_role.py`:

```python
class TestTedPatchEndpoint:
    def test_patch_ted_with_role(self, client, sample_aeroplane_id, sample_wing_name):
        resp = client.patch(
            f"/v2/aeroplanes/{sample_aeroplane_id}/wings/{sample_wing_name}/cross_sections/0/trailing_edge_device",
            json={"role": "elevator"},
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "elevator"

    def test_patch_ted_with_label(self, client, sample_aeroplane_id, sample_wing_name):
        resp = client.patch(
            f"/v2/aeroplanes/{sample_aeroplane_id}/wings/{sample_wing_name}/cross_sections/0/trailing_edge_device",
            json={"role": "aileron", "label": "Left Aileron"},
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "aileron"
        assert resp.json()["label"] == "Left Aileron"
        assert resp.json()["name"] == "Left Aileron"
```

- [ ] **Step 2: Verify no code changes needed in wing_service**

The `patch_trailing_edge_device` function uses `setattr` on all patch fields — it will automatically handle `role` and `label` since they're on both the patch schema and the ORM model. The response schema hydrates from ORM with `from_attributes=True`.

Verify by running the test. If it passes without service changes, the schema + model changes were sufficient.

- [ ] **Step 3: Run tests**

Run: `poetry run pytest app/tests/test_control_surface_role.py::TestTedPatchEndpoint -v`
Expected: PASS (may need fixtures — use existing conftest fixtures for aeroplane/wing)

- [ ] **Step 4: Commit**

```bash
git add app/tests/test_control_surface_role.py
git commit -m "test(gh-439): verify TED patch endpoint handles role/label"
```

---

### Task 6: Frontend — Role Dropdown in TedEditDialog

**Files:**
- Modify: `frontend/components/workbench/TedEditDialog.tsx`
- Modify: `frontend/components/workbench/AeroplaneTree.tsx`

- [ ] **Step 1: Add role constants**

In `TedEditDialog.tsx`, add the role options at the top of the file:

```typescript
const CONTROL_SURFACE_ROLES = [
  { value: "elevator", label: "Elevator" },
  { value: "aileron", label: "Aileron" },
  { value: "rudder", label: "Rudder" },
  { value: "elevon", label: "Elevon" },
  { value: "stabilator", label: "Stabilator" },
  { value: "flap", label: "Flap" },
  { value: "spoiler", label: "Spoiler" },
  { value: "other", label: "Other" },
] as const;

type ControlSurfaceRole = (typeof CONTROL_SURFACE_ROLES)[number]["value"];
```

- [ ] **Step 2: Add role and label state**

Add state variables:

```typescript
const [role, setRole] = useState<ControlSurfaceRole>(
  (initialData?.role as ControlSurfaceRole) ?? "other"
);
const [label, setLabel] = useState(initialData?.label ?? "");
```

- [ ] **Step 3: Update handleSave to include role and label**

In the PATCH payload for the TED endpoint, add `role` and `label`:

```typescript
const tedPayload: Record<string, unknown> = {
  role,
  ...(label.trim() ? { label: label.trim() } : { label: null }),
  rel_chord_root: parseFloat(hingePoint) || undefined,
  // ... rest of existing fields
};
```

Remove the `name` field from the payload — it's now computed server-side from role/label.

- [ ] **Step 4: Replace name input with role dropdown + label field**

Replace the name `TedField` input with:

```tsx
{/* Role dropdown */}
<div className="flex flex-col gap-1">
  <label className="text-xs text-muted-foreground">Role</label>
  <select
    value={role}
    onChange={(e) => setRole(e.target.value as ControlSurfaceRole)}
    className="h-8 rounded border border-border bg-background px-2 text-sm"
  >
    {CONTROL_SURFACE_ROLES.map((r) => (
      <option key={r.value} value={r.value}>{r.label}</option>
    ))}
  </select>
</div>

{/* Optional label */}
<TedField
  label="Label (optional)"
  value={label}
  onChange={setLabel}
  placeholder="e.g. Left Aileron"
/>
```

- [ ] **Step 5: Update AeroplaneTree TED display**

In `AeroplaneTree.tsx`, update the TED node label (around line 88):

```typescript
const tedRole = (tedObj.role as string) ?? "";
const tedLabel = (tedObj.label as string) ?? "";
const tedDisplay = tedLabel || tedRole || "TED";
```

Update line 91:
```typescript
label: `TED: ${tedDisplay}`,
```

- [ ] **Step 6: Commit**

```bash
git add frontend/components/workbench/TedEditDialog.tsx frontend/components/workbench/AeroplaneTree.tsx
git commit -m "feat(gh-439): role dropdown and label field in TedEditDialog"
```

---

### Task 7: Frontend Tests

**Files:**
- Create: `frontend/__tests__/TedEditDialog.test.tsx`

- [ ] **Step 1: Write vitest tests**

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TedEditDialog from "@/components/workbench/TedEditDialog";

describe("TedEditDialog role dropdown", () => {
  const defaultProps = {
    open: true,
    onClose: vi.fn(),
    aeroplaneId: 1,
    wingName: "Main Wing",
    xsecIndex: 0,
    isNew: true,
    initialData: null,
    onSaved: vi.fn(),
  };

  it("renders role dropdown with all options", () => {
    render(<TedEditDialog {...defaultProps} />);
    const select = screen.getByRole("combobox") || screen.getByDisplayValue("other");
    expect(select).toBeTruthy();
  });

  it("defaults role to 'other' for new TED", () => {
    render(<TedEditDialog {...defaultProps} />);
    const select = screen.getByDisplayValue("Other") as HTMLSelectElement;
    expect(select.value).toBe("other");
  });

  it("renders optional label input", () => {
    render(<TedEditDialog {...defaultProps} />);
    expect(screen.getByPlaceholderText("e.g. Left Aileron")).toBeTruthy();
  });

  it("pre-fills role from initialData", () => {
    render(
      <TedEditDialog
        {...defaultProps}
        isNew={false}
        initialData={{ role: "elevator", label: "Main Elevator" }}
      />
    );
    const select = screen.getByDisplayValue("Elevator") as HTMLSelectElement;
    expect(select.value).toBe("elevator");
  });
});
```

- [ ] **Step 2: Run frontend tests**

Run: `cd frontend && npm run test:unit`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/__tests__/TedEditDialog.test.tsx
git commit -m "test(gh-439): vitest tests for TED role dropdown"
```

---

### Task 8: Final Integration Verification

- [ ] **Step 1: Run full backend test suite**

Run: `poetry run pytest -m "not slow" --tb=short -q`
Expected: All pass

- [ ] **Step 2: Run full frontend test suite**

Run: `cd frontend && npm run test:unit`
Expected: All pass

- [ ] **Step 3: Run dependency check**

Run: `cd frontend && npm run deps:check`
Expected: No new violations

- [ ] **Step 4: Run linter**

Run: `poetry run ruff check . && poetry run ruff format --check .`
Expected: Clean

- [ ] **Step 5: Create PR**

```bash
git push github feat/gh-439-control-surface-role
gh pr create --title "feat(gh-439): standardized control surface role dropdown with flap support" \
  --body "Closes #439"
```
