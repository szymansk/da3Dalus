# Spars + TEDs als interaktive Baum-Nodes (#136)

## Problem

Spars und TEDs sind im PropertyForm versteckt und schwer zugänglich. Spars können nicht editiert oder gelöscht werden, TEDs sind nicht als eigene Entität im Baum sichtbar. Das widerspricht dem Baumkonzept: ein Segment hat N Spars und 0-1 TEDs.

## Lösung

Reine Frontend-Änderung. Spars und TEDs werden als interaktive Kinder-Nodes im Segment-Baum dargestellt mit Stift (Edit) und Mülleimer (Delete) Icons. Ein + Menü am Segment ermöglicht das Hinzufügen. SparsSection und TedSection werden aus PropertyForm entfernt.

## Baumstruktur

```
▶ segment 0                          [+] ✏️ 🗑️
  ├── root: mh32 · 150.0 mm
  ├── tip: mh32 · 120.0 mm
  ├── dims: length 500 mm · sweep 10 mm
  ├── ▶ TED: aileron                  ✏️ 🗑️
  ├── spar @ 25%    5.0×5.0 mm       ✏️ 🗑️
  └── spar @ 80%    3.0×4.0 mm       ✏️ 🗑️
```

- Die alte "spars (N)" Gruppen-Node entfällt. Spars sind direkte Kinder des Segments.
- TED wird als eigener Node angezeigt (Label: "TED: {name}").
- `+` Menü am Segment: "Add Spar" und "Add Control Surface" (letzteres nur wenn kein TED existiert).

## Dialoge

### SparEditDialog (neu)

Modaler Dialog, identisches Pattern wie PropertyForm-Modal:

| Feld | Typ | Backend-Feld |
|------|-----|-------------|
| Position (%) | Number 0-100 | `spare_position_factor` (0-1) |
| Width (mm) | Number | `spare_support_dimension_width` |
| Height (mm) | Number | `spare_support_dimension_height` |
| Mode | Select | `spare_mode` (standard/follow/normal/standard_backward/orthogonal_backward) |
| Start (mm) | Number | `spare_start` |
| Length (mm) | Number, optional | `spare_length` |

- **Neuer Spar:** Save → `POST /wings/{name}/cross_sections/{idx}/spars`
- **Edit:** Save → `PUT /wings/{name}/cross_sections/{idx}/spars/{spar_idx}`
- **Delete:** Button im Dialog → `DELETE /wings/{name}/cross_sections/{idx}/spars/{spar_idx}`

### TedEditDialog (extrahiert aus TedSection)

Bestehende TedSection-Felder in eigenständigem Modal:

| Feld | Typ | Backend-Feld |
|------|-----|-------------|
| Name | Text | `name` |
| Hinge Point | Number 0-1 | `rel_chord_root` |
| Symmetric | Checkbox | `symmetric` |
| Tip Chord | Number 0-1 | `rel_chord_tip` |
| Hinge Type | Select | `hinge_type` |
| Pos. Deflection (°) | Number | `positive_deflection_deg` |
| Neg. Deflection (°) | Number | `negative_deflection_deg` |
| Hinge Spacing (mm) | Number | `hinge_spacing` |
| Side Spacing Root (mm) | Number | `side_spacing_root` |
| Side Spacing Tip (mm) | Number | `side_spacing_tip` |
| TE Offset Factor | Number | `trailing_edge_offset_factor` |
| Servo Placement | Select | `servo_placement` (top/bottom) |
| Servo Chord Pos | Number 0-1 | `rel_chord_servo_position` |
| Servo Length Pos | Number 0-1 | `rel_length_servo_position` |

- **Save:** `PATCH /trailing_edge_device` + `PATCH /trailing_edge_device/cad_details`
- **Delete:** `DELETE /trailing_edge_device`
- **Neuer TED:** `PATCH /trailing_edge_device` mit Initialwerten

Servo-Zuweisung bleibt im TED-Dialog (bestehende Servo-Picker Logik aus TedSection).

## PropertyForm Bereinigung

- `SparsSection` (Zeilen 1163-1302) → komplett entfernen
- `TedSection` (Zeilen 907-1157) → komplett entfernen
- PropertyForm zeigt nur noch Segment-Grunddaten: Airfoil Root/Tip, Chord, Dihedral, Incidence, Sweep, Length, Rotation Point, Interpolation Points, Tip Type

## AeroplaneTree Änderungen

### Segment-Node

- `onAdd` Callback → öffnet Menü "Add Spar" / "Add Control Surface"
- Menü zeigt "Add Control Surface" nur wenn kein TED existiert

### TED-Node (neu, Level 3)

```typescript
{
  id: `${segId}-ted`,
  label: `TED: ${tedName}`,
  level: 3,
  leaf: true,
  chip: "TED",
  onEdit: () => openTedDialog(wingName, xsecIndex),
  onDelete: () => deleteTed(wingName, xsecIndex),
}
```

### Spar-Nodes (erweitert, Level 3)

```typescript
{
  id: `${segId}-spar-${s}`,
  label: `spar @ ${pos}%`,
  level: 3,
  leaf: true,
  detail: `${w}×${h} mm`,
  onEdit: () => openSparDialog(wingName, xsecIndex, s),
  onDelete: () => deleteSpar(wingName, xsecIndex, s),
}
```

## API (kein Backend-Impact)

Alle Endpoints existieren bereits:

| Aktion | Methode | Endpoint |
|--------|---------|----------|
| List Spars | GET | `/wings/{name}/cross_sections/{idx}/spars` |
| Add Spar | POST | `/wings/{name}/cross_sections/{idx}/spars` |
| Edit Spar | PUT | `/wings/{name}/cross_sections/{idx}/spars/{spar_idx}` |
| Delete Spar | DELETE | `/wings/{name}/cross_sections/{idx}/spars/{spar_idx}` |
| Edit TED | PATCH | `/wings/{name}/cross_sections/{idx}/trailing_edge_device` |
| Delete TED | DELETE | `/wings/{name}/cross_sections/{idx}/trailing_edge_device` |
| Edit TED CAD | PATCH | `/wings/{name}/cross_sections/{idx}/control_surface/cad_details` |
| Edit Servo | PATCH | `/wings/{name}/cross_sections/{idx}/control_surface/cad_details/servo_details` |

## Tests (Vitest)

### SparEditDialog.test.tsx (6 Tests)

1. Rendert alle Felder (position, width, height, mode, start, length)
2. Save-Button disabled wenn Pflichtfelder leer
3. Save ruft POST für neuen Spar auf
4. Save ruft PUT für bestehenden Spar auf
5. Delete-Button ruft DELETE und schließt Dialog
6. Cancel schließt Dialog ohne API-Call

### TedEditDialog.test.tsx (5 Tests)

1. Rendert alle TED-Felder
2. Save ruft PATCH trailing_edge_device
3. Delete-Button ruft DELETE und schließt Dialog
4. Neuer TED: Save ruft PATCH mit Initialwerten
5. Cancel schließt Dialog ohne API-Call

### AeroplaneTree Spar/TED Integration (4 Tests)

1. Segment mit Spars zeigt Spar-Nodes mit Edit/Delete Icons
2. Segment mit TED zeigt TED-Node mit Edit/Delete Icons
3. + Menü zeigt nur "Add Spar" wenn TED existiert
4. + Menü zeigt "Add Spar" + "Add Control Surface" wenn kein TED

## Dateien

| Datei | Aktion |
|-------|--------|
| `frontend/components/workbench/SparEditDialog.tsx` | NEU |
| `frontend/components/workbench/TedEditDialog.tsx` | NEU (extrahiert aus PropertyForm) |
| `frontend/components/workbench/AeroplaneTree.tsx` | MODIFY — Spar/TED Nodes interaktiv |
| `frontend/components/workbench/PropertyForm.tsx` | MODIFY — SparsSection + TedSection entfernen |
| `frontend/app/workbench/page.tsx` | MODIFY — Dialog-State + Callbacks |
| `frontend/__tests__/SparEditDialog.test.tsx` | NEU |
| `frontend/__tests__/TedEditDialog.test.tsx` | NEU |
| `frontend/__tests__/AeroplaneTreeSparTed.test.tsx` | NEU |
