# Implementation Plan: GH #45 — Shared Workbench Layout-Komponenten

## Context

**Problem:** 5 von 6 Workbench-Screens nutzen identische Layout-Patterns (Two-Panel, Tree-Card-Shell, Alert-Banner). Aktuell ist jede Page einzeln strukturiert, was zu Duplikation (3x identischer Alert-Block) und inkonsistenter Umsetzung führt.

**Desired Outcome:** 4 shared Komponenten (`TreeCard`, `WorkbenchTwoPanel`, `AlertBanner`, `SplitHandle`) als Grundlage für alle Screen-Refactors in Epic #44.

**Wireframe-Referenz:** `da3Dalus.pen` — Pattern sichtbar in `screen-1-mission`, `screen-3-analysis`, `screen-4-components`, `screen-5-weight`

**Part of:** Epic #44 (Frontend Wireframe Redesign)
**Blocks:** #47, #48, #49, #50, #51

---

## Scope

### In Scope (Acceptance Criteria aus GH #45)
1. `TreeCard` rendert Header + scrollbaren Body, akzeptiert `title` + `children`
2. `WorkbenchTwoPanel` erzeugt Two-Panel-Layout mit konfigurierbarer linker Breite
3. `AlertBanner` ersetzt die 3 duplizierten Alert-Blocks in Mission/Components/Weight
4. `SplitHandle` zeigt Grip-Dots und Collapse-Chevron, funktioniert mit `react-resizable-panels`
5. Alle Komponenten haben Unit Tests
6. `npm run build` fehlerfrei

### Out of Scope
- Einbau in bestehende Pages (eigene Issues #47–#51)
- Resizable Variante von TwoPanel
- Backend-Änderungen

---

## Architecture Constraints

| Constraint | Specification | Source |
|-----------|--------------|--------|
| React 19 | `react@19.2.5`, `react-dom@19.2.5` | `package.json` |
| Next.js Canary | `next@16.2.1-canary.33`, App Router | `package.json`, `CLAUDE.md` |
| Dark Theme | Orange accent `#FF8400`, JetBrains Mono + Geist | `frontend/CLAUDE.md` |
| Tailwind 4 | `tailwindcss@4`, CSS variables for tokens | `package.json` |
| Pencil First | All UI changes must match `da3Dalus.pen` wireframe | `CLAUDE.md` |
| react-resizable-panels | `v4.10.0`, imports `Group`, `Panel`, `Separator` | `package.json` |
| Test Framework | vitest 4.1.4 + @testing-library/react 16.3 | `package.json` |

---

## Key Design Decisions

### Decision 1: TreeCard als reine Shell, nicht als generalisierter Tree

**Decision:** `TreeCard` ist nur die visuelle Card-Hülle (Header + scrollbarer Body). Die Tree-Logik (Expand/Collapse, Daten) bleibt in den jeweiligen Tree-Komponenten.

**Rationale:** Der bestehende `AeroplaneTree.tsx` (505 LOC) hat hochspezifische Logik (WingConfig vs ASB modes, segment CRUD). Diese zu generalisieren wäre riskant und ein Breaking Change. TreeCard extrahiert nur das visuelle Pattern, das in der Wireframe-`component/AeroplaneTree` Node identisch wiederverwendet wird.

### Decision 2: WorkbenchTwoPanel ohne Resize

**Decision:** `WorkbenchTwoPanel` ist ein einfacher Flex-Container mit fixer linker Breite. Kein `react-resizable-panels`.

**Rationale:** Construction + Analysis brauchen Resize (User zieht CAD Viewer größer). Mission, Components, Weight haben statische Layouts wo Resize keinen Wert hat. Zwei verschiedene Layout-Mechanismen statt einen zu überladen.

### Decision 3: SplitHandle als PanelResizeHandle-Wrapper

**Decision:** `SplitHandle` implementiert die `react-resizable-panels` `PanelResizeHandle`-API (ersetzt `<Separator>`), nicht eine eigene Drag-Logik.

**Rationale:** `react-resizable-panels` v4 unterstützt custom children in `PanelResizeHandle`. Eigene Drag-Logik wäre redundant und fehleranfällig. Die Collapse-Funktion nutzt die `Panel.collapse()`/`expand()` API via imperative handle.

### Decision 4: AlertBanner mit title + children statt title + body

**Decision:** `AlertBanner` Props: `{ title: string; children: ReactNode }` statt `{ title: string; body: string }`.

**Rationale:** Die Wireframes zeigen teilweise Beads-Issue-Referenzen im Body-Text (`cad-modelling-service-yu9`). Mit `children` kann der Konsument beliebige Inhalte (Links, Code) einbetten. Die 3 aktuellen Anwendungsfälle sind trivial (`<AlertBanner title="...">text</AlertBanner>`).

---

## Project Structure

```
frontend/
├── components/workbench/
│   ├── TreeCard.tsx              NEW — Card-Shell für Tree-Panels
│   ├── WorkbenchTwoPanel.tsx     NEW — Two-Panel Layout ohne Resize
│   ├── AlertBanner.tsx           NEW — Shared Alert Banner
│   ├── SplitHandle.tsx           NEW — Custom Split Handle
│   ├── AeroplaneTree.tsx         EXISTING — wird TreeCard konsumieren (späteres Issue)
│   ├── AnalysisConfigPanel.tsx   EXISTING — konsumiert SplitHandle (späteres Issue)
│   └── ...
├── __tests__/
│   ├── TreeCard.test.tsx         NEW
│   ├── WorkbenchTwoPanel.test.tsx NEW
│   ├── AlertBanner.test.tsx      NEW
│   └── SplitHandle.test.tsx      NEW
└── package.json                  EXISTING — keine Änderungen nötig
```

---

## Module Specifications

### 1. TreeCard

**Datei:** `frontend/components/workbench/TreeCard.tsx`
**Verantwortung:** Visuelle Card-Shell für Tree-Panels mit Header und scrollbarem Body.

```tsx
// Props
interface TreeCardProps {
  title: string;
  badge?: string;              // z.B. "1.177 kg" im Weight Tree
  badgeVariant?: "primary" | "muted";
  actions?: React.ReactNode;   // z.B. Mode-Toggle, Plus-Button
  children: React.ReactNode;   // Tree-Content
  className?: string;
}

// Sketch
export function TreeCard({ title, badge, badgeVariant, actions, children, className }: TreeCardProps) {
  return (
    <div className={cn("rounded-[--radius-m] border border-border bg-card overflow-hidden flex flex-col", className)}>
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          {title}
        </span>
        {badge && <span className={cn("...", badgeVariant)}>{badge}</span>}
        <div className="flex-1" />
        {actions}
      </div>
      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-4 pb-3">
        {children}
      </div>
    </div>
  );
}
```

**Design Points:**
- Spiegelt das Pattern aus `AeroplaneTree.tsx` Zeile 369-415 (outer div)
- Wireframe `component/AeroplaneTree` Node `k7wab`: `cornerRadius: --radius-m`, `fill: --card`, `stroke: --border`, `padding: [12,16]`, `gap: 4`, `clip: true`
- `overflow-y-auto` auf Body für scrollbare Trees
- `actions` Slot für mode-toggle (AeroplaneTree) oder add-buttons (WeightTree)

**Tests:** 4 Tests
- Rendert Titel
- Rendert Badge mit korrektem Variant
- Rendert Actions-Slot
- Scrollbar bei Overflow

### 2. WorkbenchTwoPanel

**Datei:** `frontend/components/workbench/WorkbenchTwoPanel.tsx`
**Verantwortung:** Einfaches Two-Panel-Layout mit fixer linker Breite.

```tsx
interface WorkbenchTwoPanelProps {
  leftWidth?: number;           // default 360
  children: React.ReactNode;    // erwartet genau 2 Kinder
  className?: string;
}

// Sketch
export function WorkbenchTwoPanel({ leftWidth = 360, children, className }: WorkbenchTwoPanelProps) {
  const [left, right] = React.Children.toArray(children);
  return (
    <div className={cn("flex flex-1 gap-4 overflow-hidden", className)}>
      <div style={{ width: leftWidth, minWidth: leftWidth }} className="shrink-0 overflow-hidden">
        {left}
      </div>
      <div className="flex-1 overflow-hidden">
        {right}
      </div>
    </div>
  );
}
```

**Design Points:**
- Wireframe zeigt konsistent: linkes Panel 360px, gap 16px (Tailwind `gap-4`), rechtes Panel `fill_container`
- Workbench Layout (`layout.tsx`) setzt `p-4 gap-4` auf `<main>` — TwoPanel muss `flex-1 overflow-hidden` sein
- Kein `react-resizable-panels` — bewusst einfach gehalten
- `shrink-0` auf links verhindert Quetschung

**Tests:** 4 Tests
- Rendert zwei Kinder nebeneinander
- Linkes Panel hat korrekte Breite (default 360)
- Custom leftWidth wird übernommen
- Overflow wird auf beiden Panels gehidden

### 3. AlertBanner

**Datei:** `frontend/components/workbench/AlertBanner.tsx`
**Verantwortung:** Orange Alert-Banner für "Coming soon"-Hinweise.

```tsx
interface AlertBannerProps {
  title?: string;               // default "Coming soon — backend wiring in progress"
  children: React.ReactNode;    // Body-Text
}

// Sketch
export function AlertBanner({ title = "Coming soon — backend wiring in progress", children }: AlertBannerProps) {
  return (
    <div className="flex items-start gap-3 rounded-[--radius-s] border border-primary bg-[#2A1F10] p-4">
      <Info className="size-4 shrink-0 text-primary" />
      <div className="flex flex-col gap-0.5">
        <span className="text-[13px] font-semibold text-foreground">
          {title}
        </span>
        <span className="text-[12px] text-muted-foreground">
          {children}
        </span>
      </div>
    </div>
  );
}
```

**Design Points:**
- Exakt das duplizierte Pattern aus Mission/Components/Weight (identische Klassen)
- Default-Title deckt den häufigsten Fall ab
- `children` statt `body: string` für Flexibilität (Links, Beads-Referenzen)

**Tests:** 3 Tests
- Rendert Default-Title + children
- Rendert Custom-Title
- Info-Icon ist sichtbar

### 4. SplitHandle

**Datei:** `frontend/components/workbench/SplitHandle.tsx`
**Verantwortung:** Custom Split Handle für `react-resizable-panels` mit Grip-Dots und Collapse-Button.

```tsx
import { PanelResizeHandle } from "react-resizable-panels";

interface SplitHandleProps {
  onCollapse?: () => void;
  collapsed?: boolean;
}

// Sketch
export function SplitHandle({ onCollapse, collapsed }: SplitHandleProps) {
  return (
    <PanelResizeHandle className="group relative flex w-1 items-center justify-center bg-border transition-colors hover:bg-primary/50">
      {/* Grip dots */}
      <div className="flex flex-col gap-1">
        {[0, 1, 2].map((i) => (
          <div key={i} className="size-[3px] rounded-full bg-muted-foreground opacity-50" />
        ))}
      </div>
      {/* Collapse chevron */}
      {onCollapse && (
        <button
          onClick={onCollapse}
          className="absolute -left-1.5 top-1/2 flex w-4 h-6 -translate-y-1/2 items-center justify-center rounded-[--radius-xs] border border-border bg-card-muted"
        >
          <ChevronRight size={12} className={cn("text-muted-foreground transition-transform", !collapsed && "rotate-180")} />
        </button>
      )}
    </PanelResizeHandle>
  );
}
```

**Design Points:**
- Wireframe Node `9fOlp`/`PWy49`: `width: 4`, `fill: --border`, 3 Grip-Dots (`ellipse 3×3`, `opacity: 0.5`), Chevron-Button (`16×24`, `cornerRadius: 4`, `absolute position x:-6`)
- `PanelResizeHandle` ersetzt `<Separator>` — Drop-in Replacement in bestehenden Pages
- Collapse-Button ist optional (`onCollapse` prop) — nicht alle Panels brauchen Collapse
- `collapsed` steuert Chevron-Richtung (rechts = expand, links = collapse)

**Tests:** 5 Tests
- Rendert 3 Grip-Dots
- Rendert Collapse-Button wenn `onCollapse` übergeben
- Kein Collapse-Button ohne `onCollapse`
- Chevron rotiert bei `collapsed=true`
- Click auf Collapse ruft `onCollapse` auf

---

## Test Strategy

**Coverage Target:** >90% für alle 4 neuen Komponenten

**Test Framework:** vitest + @testing-library/react (bestehendes Pattern)

| Modul | Unit Tests | Gesamt |
|-------|-----------|--------|
| TreeCard | 4 | 4 |
| WorkbenchTwoPanel | 4 | 4 |
| AlertBanner | 3 | 3 |
| SplitHandle | 5 | 5 |
| **Total** | **16** | **16** |

**Mock Patterns:**
- `react-resizable-panels`: Mock `PanelResizeHandle` als `div` mit `onMouseDown`
- `lucide-react`: Mock Icons als simple SVG-Placeholder (Pattern aus `StreamlinesViewer.test.tsx`)

**Quality Gates:**
1. `npx vitest run` — alle 16 Tests grün
2. `npm run build` — keine TypeScript-Errors
3. Visueller Vergleich gegen `da3Dalus.pen` Screenshots

---

## Verification

| AC | Test/Evidence |
|----|---------------|
| TreeCard rendert Header + scrollbaren Body | `TreeCard.test.tsx` — Render + overflow test |
| WorkbenchTwoPanel mit konfigurierbarer Breite | `WorkbenchTwoPanel.test.tsx` — Default + custom width |
| AlertBanner ersetzt duplizierte Blocks | `AlertBanner.test.tsx` — Render mit default/custom title |
| SplitHandle mit Grip-Dots + Collapse | `SplitHandle.test.tsx` — Dots, button, rotation, click |
| Alle Komponenten haben Tests | 16 Tests über 4 Dateien |
| `npm run build` fehlerfrei | CI build step |

---

## Forward Compatibility

| Downstream Issue | Readiness | Integration Point |
|-----------------|-----------|-------------------|
| #47 Mission Radar | TreeCard nicht benötigt, WorkbenchTwoPanel + AlertBanner | TwoPanel links=RadarChart, rechts=Form |
| #48 Components Tree | TreeCard + WorkbenchTwoPanel + AlertBanner | TreeCard wraps ComponentTree |
| #49 Weight Tree | TreeCard + WorkbenchTwoPanel + AlertBanner | TreeCard wraps WeightTree mit badge |
| #50 Airfoil Preview | WorkbenchTwoPanel-Pattern (aber mit Resize) | Ggf. eigenes Layout, nicht TwoPanel |
| #51 Analysis Handle | SplitHandle | Drop-in für `<Separator>` |

---

## Key References

| Document | Path | Relevance |
|----------|------|-----------|
| GH Issue #45 | github.com/szymansk/da3Dalus/issues/45 | Epic specification |
| Wireframe | `da3Dalus.pen` | Visual spec für alle Komponenten |
| AeroplaneTree | `frontend/components/workbench/AeroplaneTree.tsx:369-415` | TreeCard Shell-Pattern |
| Alert duplication | `mission/page.tsx:44`, `components/page.tsx:101`, `weight/page.tsx:57` | AlertBanner Extraktion |
| Analysis Separator | `workbench/page.tsx:36` | SplitHandle Replace-Target |
| Test patterns | `frontend/__tests__/StreamlinesViewer.test.tsx` | Component test Pattern |
