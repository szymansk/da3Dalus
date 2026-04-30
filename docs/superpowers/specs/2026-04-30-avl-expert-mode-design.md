# AVL Expert Mode — Geometry File Editor

## Problem

AVL-based analyses (Trefftz Plane, Polar, Streamlines) use a geometry
file generated automatically from the airplane's wing/fuselage data.
Power users need the ability to inspect, edit, and persist this file
to fine-tune AVL paneling, add custom sections, or fix geometry issues
that the automatic converter doesn't handle well (e.g. high-section-count
wings exceeding AVL's panel limits).

Currently, the generated `.avl` file is ephemeral — written to a temp
directory, used once, and discarded. There is no way to inspect or
modify it.

## Proposal

### Overview

An Expert Mode that lets users view and edit the AVL geometry file
(`.avl`) in a full-featured code editor. The edited file is persisted
in the database and used for all subsequent AVL analyses until reset
or marked dirty by geometry changes.

### UI Flow

1. In the **Configure & Run** modal (for AVL-based analyses only),
   an **"Edit AVL Geometry"** button opens a separate editor dialog.
2. The editor dialog contains a **Monaco Editor** with AVL syntax
   highlighting, dark theme, and JetBrains Mono font.
3. The dialog is **maximizable to full window** — no editing through
   a keyhole.
4. On first open (no saved file), the backend **lazy-generates** the
   `.avl` file and returns it. No impact on existing flow until the
   user actually opens Expert Mode.
5. The user can edit and **Save** — the file is persisted and used
   for all future AVL analyses on this aeroplane.
6. **"Reset to Generated"** discards the user's edits and regenerates
   from current geometry.

### Dirty Flag & Diff Workflow

When the airplane geometry changes (wings, fuselages, xsecs), the
saved geometry file is marked **dirty** via a SQLAlchemy event hook
on `WingModel`, `WingXSecModel`, `FuselageModel`
(`after_insert` / `after_update` / `after_delete`).

When the user opens the editor with a dirty file:

1. A **warning** is shown: "Airplane geometry has changed since you
   last edited the AVL file."
2. The user chooses:
   - **"View Diff"** — Opens the Monaco DiffEditor showing the
     **full file** (old edited version left, newly generated right).
     The user can edit the right side to merge changes from the old
     version. Save persists the right side and clears the dirty flag.
   - **"Regenerate"** — Discards the old edits, generates fresh,
     clears dirty flag. Opens the normal editor.

### Backend

#### Database Model

New table `avl_geometry_files`:

```
id              Integer PK
aeroplane_id    UUID FK(aeroplanes.uuid) UNIQUE, ON DELETE CASCADE
content         Text NOT NULL        -- the .avl file content
is_dirty        Boolean DEFAULT FALSE
is_user_edited  Boolean DEFAULT FALSE
created_at      DateTime
updated_at      DateTime
```

One row per aeroplane (nullable — no row means "never opened Expert
Mode"). Alembic migration required.

#### Dirty Flag — SQLAlchemy Event Hook

A single listener registration point that listens on geometry-relevant
models:

- `WingModel`: after_insert, after_update, after_delete
- `WingXSecModel`: after_insert, after_update, after_delete
- `FuselageModel`: after_insert, after_update, after_delete

On any of these events, set `is_dirty = True` on the corresponding
`avl_geometry_files` row (if it exists). No-op if no Expert Mode
file has been saved yet.

#### API Endpoints

```
GET  /aeroplanes/{id}/avl-geometry
     → Returns { content, is_dirty, is_user_edited }
     → If no saved file: generates from current geometry, returns
       with is_user_edited=false (does NOT persist yet)

PUT  /aeroplanes/{id}/avl-geometry
     Body: { content }
     → Saves/updates the file, sets is_user_edited=true,
       clears is_dirty

POST /aeroplanes/{id}/avl-geometry/regenerate
     → Generates fresh from current geometry, returns content
     → Does NOT persist (user decides via Save in the editor)

DELETE /aeroplanes/{id}/avl-geometry
     → Deletes saved file, future analyses use generated version
```

#### Analysis Integration

All AVL analysis functions (`analyze_airplane_strip_forces`,
`analyze_airplane_alpha_sweep`, etc.) check before running:

1. Load `avl_geometry_files` for this aeroplane
2. If `is_user_edited=True`: write `content` to the temp directory
   as the `.avl` file, skip `self.write_avl()`
3. If not: normal flow (generate via aerosandbox)

### Frontend

#### Editor Component: `<AvlGeometryEditor>`

Self-contained, reusable component. Props:

```typescript
interface AvlGeometryEditorProps {
  aeroplaneId: string;
  open: boolean;
  onClose: () => void;
}
```

Internally manages:
- Fetching/saving geometry via the API
- Normal editor vs. diff editor mode
- Dirty warning dialog
- Fullscreen toggle

#### Technology

- **`@monaco-editor/react`** — dynamic import, `ssr: false`
- **Custom AVL language** — Monarch tokenizer for keywords
  (`SURFACE`, `SECTION`, `YDUPLICATE`, `AFIL`, `CLAF`, `CDCL`,
  `CONTROL`, `BODY`), comments (`!`, `#`), numbers
- **DiffEditor** — full-file side-by-side diff for dirty state
- **Dark theme** matching the app, JetBrains Mono font

#### Integration Point

In `AnalysisConfigPanel.tsx`: conditionally render the "Edit AVL
Geometry" button when the active analysis type is AVL-based
(Trefftz Plane, Polar, Streamlines). Button opens the
`<AvlGeometryEditor>` dialog.

### AVL File Generation

The generation reuses the existing pipeline:

1. Load `AeroplaneSchema` from DB
2. Convert to `asb.Airplane` via `aeroplane_schema_to_asb_airplane_async()`
3. Create `asb.AVL(airplane=..., op_point=dummy_op_point)`
4. Call `write_avl()` to a temp file
5. Read and return the file content as string

A dummy operating point is used because the geometry file is
independent of the operating point (that's the run file, which
is out of scope for now).

## Acceptance Criteria

- [ ] New DB table `avl_geometry_files` with Alembic migration
- [ ] SQLAlchemy event hooks set `is_dirty` on geometry changes
- [ ] `GET /aeroplanes/{id}/avl-geometry` returns content (lazy gen)
- [ ] `PUT /aeroplanes/{id}/avl-geometry` persists edited content
- [ ] `POST /aeroplanes/{id}/avl-geometry/regenerate` returns fresh
- [ ] `DELETE /aeroplanes/{id}/avl-geometry` removes saved file
- [ ] All AVL analyses use saved geometry file when `is_user_edited`
- [ ] `<AvlGeometryEditor>` component with Monaco Editor
- [ ] AVL syntax highlighting (keywords, comments, numbers)
- [ ] Fullscreen / maximize support
- [ ] Dirty warning with "View Diff" / "Regenerate" options
- [ ] Monaco DiffEditor shows full file for dirty state
- [ ] "Edit AVL Geometry" button in Configure & Run modal
- [ ] Button only visible for AVL-based analysis types

## Dependencies

- `@monaco-editor/react` npm package (new dependency)
- Existing AVL analysis infrastructure (`avl_strip_forces.py`,
  `analysis_service.py`)
- Existing aeroplane-to-ASB converter pipeline

## Out of Scope

- AVL **run file** / operating point editor (planned as follow-up)
- Versioning of geometry file edits (single active version only)
- Auto-merge of user edits with regenerated geometry
- Expert mode for non-AVL analyses (AeroBuildup, VLM)
