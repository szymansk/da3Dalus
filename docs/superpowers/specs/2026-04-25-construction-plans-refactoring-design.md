# Construction Plans & Templates — User-Driven Redesign

**GitHub Issue:** #320
**Date:** 2026-04-25

## Context

The Construction Plans page needs a fundamental redesign driven by the
user's actual workflow. The user always starts from an aeroplane and
works on multiple partial plans (wings, fuselage, motor mount). The
current UI doesn't reflect this — it mixes plan/template concerns in a
single 1064-line component, lacks drag-and-drop from the Creator gallery,
hides input/output shapes, and uses inline parameter editing instead of
the project-standard modal dialog pattern.

## Core Concepts

- **Plan** = always bound to a specific aeroplane, represents a partial
  aspect (wings, fuselage, motor mount, etc.)
- **Template** = unbound, reusable blueprint tested against different
  aeroplanes
- **Entry point** = always from the selected aeroplane; Plan mode is the
  default

## Layout — Plan Mode (Default)

### Left Panel: Collapsible Plan Trees

All plans of the current aeroplane shown as collapsible sections:

```
[ Play All ]  Construction Plans
  ▾ Wing Construction          [▶ Play] [💾 Template] [✎ Rename]
    ├─ VaseWingCreator         [✎ Edit]
    │   ├─ ⬇ wing_config      (input, muted)
    │   └─ ⬆ vase_wing        (output, muted)
    └─ MirrorCreator           [✎ Edit]
        ├─ ⬇ vase_wing        (input, muted)
        └─ ⬆ mirrored_wing    (output, muted)
  ▸ Fuselage Build             [▶ Play] [💾 Template] [✎ Rename]
  ▸ Motor Mount                [▶ Play] [💾 Template] [✎ Rename]
```

- Root node = **editable plan name** (not "root")
- Input/output shapes as **muted child entries** under each Creator
  (pattern from `AeroplaneTree.tsx` segment details)
- Only **dedicated** inputs (e.g., minuend, subtrahend), not `**kwargs`
- D&D to reorder/reparent Creator nodes (root immovable)
- Play, Save-as-Template, Edit buttons on root/Creator nodes

### Right Panel: Creator Gallery

- Searchable, filterable by category (unchanged)
- **Drag-and-drop** from gallery into plan tree to add Creator

## Layout — Template Mode

- **Toggle** Plan (left, default) / Templates (right) — stays as-is
  but with corrected default and position
- **Single template** view (no collapsible list)
- **Template selector**: dropdown with search (project standard, same
  style as Servo selector in TED dialog)
- Tree is **identical** to plan tree in behavior (D&D, edit modal,
  input/output shapes, editable name at root)
- **Play button** → aeroplane selection dialog with search

## Plan Creation

- New plan: **empty** or **from existing template**
- Plan can be saved as template (button at root node)

## Parameter Editing

- **Modal dialog only** (like current AddStep dialog)
- Accessible via **edit button** on each Creator node (project pattern)

## Execution & Artifacts

- Results shown in **modal 3D viewer** (unchanged)
- Backend assigns **dedicated artifact directory** per execution
- All Creator paths are **relative** to this directory
- **Artifact browser** button → modal dialog:
  - List files in artifact directory
  - Download / delete files
  - Open file/subfolder in Finder/Explorer

## Quality & UX

- **Validation** before execution: required params set, shape refs valid
- **Undo/Redo** for tree modifications

## Acceptance Criteria

See GitHub Issue #320 for the full checklist.
