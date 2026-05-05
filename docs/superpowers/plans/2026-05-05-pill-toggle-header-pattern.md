# GH-405: PillToggle Header Pattern — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract inline toggle patterns into a shared `PillToggle` component, add a header row to the Construction tab (toggle left, "Configuration" heading right), and retrofit the Components and Construction Plans tabs.

**Architecture:** New shared component in `frontend/components/ui/PillToggle.tsx` with generic typed API. TDD — tests first, then component, then integration into three page files. Each page retrofit is a pure refactor (identical visual output).

**Tech Stack:** React 19, TypeScript, lucide-react, Tailwind CSS, vitest, @testing-library/react, userEvent

---

### Task 1: PillToggle Unit Tests (RED)

**Files:**
- Create: `frontend/__tests__/PillToggle.test.tsx`

- [ ] **Step 1: Create test file**

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = ({ size, ...rest }: Record<string, unknown>) =>
    React.createElement("span", { "data-testid": `icon-${size}`, ...rest });
  return { Package: icon, Box: icon };
});

import { PillToggle } from "@/components/ui/PillToggle";
import { Package, Box } from "lucide-react";

type View = "library" | "construction";

const OPTIONS = [
  { value: "library" as View, label: "Library", icon: Package },
  { value: "construction" as View, label: "Construction Parts", icon: Box },
];

describe("PillToggle", () => {
  it("renders all option labels", () => {
    render(<PillToggle options={OPTIONS} value="library" onChange={() => {}} />);
    expect(screen.getByText("Library")).toBeDefined();
    expect(screen.getByText("Construction Parts")).toBeDefined();
  });

  it("applies active styling to the selected option", () => {
    render(<PillToggle options={OPTIONS} value="library" onChange={() => {}} />);
    const activeBtn = screen.getByText("Library").closest("button")!;
    expect(activeBtn.className).toContain("bg-primary");
    const inactiveBtn = screen.getByText("Construction Parts").closest("button")!;
    expect(inactiveBtn.className).not.toContain("bg-primary");
  });

  it("calls onChange with the clicked option value", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<PillToggle options={OPTIONS} value="library" onChange={onChange} />);
    await user.click(screen.getByText("Construction Parts"));
    expect(onChange).toHaveBeenCalledWith("construction");
  });

  it("calls onChange even when clicking the already-active option", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<PillToggle options={OPTIONS} value="library" onChange={onChange} />);
    await user.click(screen.getByText("Library"));
    expect(onChange).toHaveBeenCalledWith("library");
  });

  it("uses custom isActive when provided", () => {
    const isActive = (opt: View, cur: View) =>
      opt === cur || (opt === "construction" && cur === "library");
    render(
      <PillToggle options={OPTIONS} value="library" onChange={() => {}} isActive={isActive} />,
    );
    // Both should be active with this custom comparator
    const libraryBtn = screen.getByText("Library").closest("button")!;
    const constructionBtn = screen.getByText("Construction Parts").closest("button")!;
    expect(libraryBtn.className).toContain("bg-primary");
    expect(constructionBtn.className).toContain("bg-primary");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run __tests__/PillToggle.test.tsx`
Expected: FAIL — module `@/components/ui/PillToggle` not found.

- [ ] **Step 3: Commit failing tests**

```bash
git add frontend/__tests__/PillToggle.test.tsx
git commit -m "test(gh-405): add failing PillToggle unit tests (RED)"
```

---

### Task 2: PillToggle Component (GREEN)

**Files:**
- Create: `frontend/components/ui/PillToggle.tsx`

- [ ] **Step 1: Create the component**

```tsx
import type { LucideIcon } from "lucide-react";

export interface PillToggleOption<T extends string> {
  value: T;
  label: string;
  icon: LucideIcon;
}

interface PillToggleProps<T extends string> {
  options: PillToggleOption<T>[];
  value: T;
  onChange: (value: T) => void;
  isActive?: (optionValue: T, currentValue: T) => boolean;
}

export function PillToggle<T extends string>({
  options,
  value,
  onChange,
  isActive,
}: Readonly<PillToggleProps<T>>) {
  const check = isActive ?? ((opt: T, cur: T) => opt === cur);

  return (
    <div className="flex items-center gap-1 rounded-full border border-border bg-card p-1">
      {options.map((opt) => {
        const active = check(opt.value, value);
        const Icon = opt.icon;
        return (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[12px] transition-colors ${
              active
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon size={12} />
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd frontend && npx vitest run __tests__/PillToggle.test.tsx`
Expected: PASS — all 5 tests green.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ui/PillToggle.tsx
git commit -m "feat(gh-405): add shared PillToggle component (GREEN)"
```

---

### Task 3: Construction Tab — Add Header Row

**Files:**
- Modify: `frontend/app/workbench/page.tsx`
- Modify: `frontend/components/workbench/AeroplaneTree.tsx`

- [ ] **Step 1: Add header row to the Construction page**

In `frontend/app/workbench/page.tsx`:

1. Add imports at the top of the file:

```tsx
import { GalleryHorizontal, GalleryHorizontalEnd, Plane } from "lucide-react";
import { PillToggle } from "@/components/ui/PillToggle";
import type { TreeMode } from "@/components/workbench/AeroplaneContext";
```

2. Add `setTreeMode` to the destructured `useAeroplaneContext()` call on line 22. The current destructuring is:

```tsx
  const {
    aeroplaneId,
    selectedWing, selectedXsecIndex, selectXsec,
    selectedFuselage, selectedFuselageXsecIndex, selectFuselageXsec,
    treeMode,
    openPicker,
    hydrated,
  } = useAeroplaneContext();
```

Add `setTreeMode` after `treeMode`:

```tsx
  const {
    aeroplaneId,
    selectedWing, selectedXsecIndex, selectXsec,
    selectedFuselage, selectedFuselageXsecIndex, selectFuselageXsec,
    treeMode, setTreeMode,
    openPicker,
    hydrated,
  } = useAeroplaneContext();
```

3. Define the toggle options constant inside the component, before the early return (before line 155):

```tsx
  const treeModeOptions: PillToggleOption<TreeMode>[] = [
    { value: "wingconfig", label: "Segments", icon: GalleryHorizontal },
    { value: "asb", label: "X-Secs", icon: GalleryHorizontalEnd },
  ];
```

You need to import `PillToggleOption` from `@/components/ui/PillToggle` as well — add it to the existing import:

```tsx
import { PillToggle, type PillToggleOption } from "@/components/ui/PillToggle";
```

4. Wrap the existing layout in a flex column and add the header row. The current return (starting at line 163) is:

```tsx
    return (
      <>
        <div className="flex h-full min-h-0 flex-1 gap-4 overflow-hidden">
          {/* Tree Panel — collapsible, fixed width, scrollable */}
```

Replace the opening with:

```tsx
    return (
      <>
        <div className="flex h-full min-h-0 flex-1 flex-col gap-3 overflow-hidden">
          {/* Header row: toggle left, heading right */}
          <div className="flex items-center gap-2">
            <PillToggle
              options={treeModeOptions}
              value={treeMode}
              onChange={setTreeMode}
              isActive={(opt, cur) => opt === cur || (opt === "asb" && cur === "fuselage")}
            />
            <div className="flex-1" />
            <div className="flex items-center gap-2.5">
              <Plane className="size-5 text-primary" />
              <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-[20px] text-foreground">
                Configuration
              </h1>
            </div>
          </div>

          <div className="flex min-h-0 flex-1 gap-4 overflow-hidden">
            {/* Tree Panel — collapsible, fixed width, scrollable */}
```

And at the end of the two-panel layout (after the closing `</div>` for the Preview panel, before the `<dialog>` for configuration modal), add the matching closing `</div>`:

The current structure around line 243-246 is:

```tsx
          </div>
        </div>
```

It becomes:

```tsx
          </div>
          </div>
        </div>
```

- [ ] **Step 2: Remove toggle from AeroplaneTree**

In `frontend/components/workbench/AeroplaneTree.tsx`, replace the header section (lines 808-845):

Current:

```tsx
      {/* Header with collapse + mode toggle */}
      <div className="mb-2 flex items-center gap-2">
        {onCollapseTree && (
          <button
            onClick={onCollapseTree}
            className="flex size-6 items-center justify-center rounded-xl text-muted-foreground hover:bg-sidebar-accent"
            title="Collapse tree panel"
          >
            <PanelLeftClose size={14} />
          </button>
        )}
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          Aeroplane Tree
        </span>
        <div className="flex-1" />
        <div className="flex shrink-0 gap-0.5 rounded-full border border-primary/60 bg-card-muted p-0.5">
          <button
            onClick={() => setTreeMode("wingconfig")}
            className={`whitespace-nowrap rounded-full px-3.5 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] transition-colors ${
              treeMode === "wingconfig"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Segments
          </button>
          <button
            onClick={() => setTreeMode("asb")}
            className={`whitespace-nowrap rounded-full px-3.5 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] transition-colors ${
              treeMode === "asb" || treeMode === "fuselage"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            X-Secs
          </button>
        </div>
      </div>
```

Replace with:

```tsx
      {/* Header with collapse button */}
      <div className="mb-2 flex items-center gap-2">
        {onCollapseTree && (
          <button
            onClick={onCollapseTree}
            className="flex size-6 items-center justify-center rounded-xl text-muted-foreground hover:bg-sidebar-accent"
            title="Collapse tree panel"
          >
            <PanelLeftClose size={14} />
          </button>
        )}
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          Aeroplane Tree
        </span>
      </div>
```

- [ ] **Step 3: Run all frontend unit tests**

Run: `cd frontend && npx vitest run`
Expected: ALL PASS — no regressions.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/workbench/page.tsx frontend/components/workbench/AeroplaneTree.tsx
git commit -m "feat(gh-405): add header row with PillToggle to Construction tab"
```

---

### Task 4: Retrofit Components Tab

**Files:**
- Modify: `frontend/app/workbench/components/page.tsx`

- [ ] **Step 1: Replace inline toggle with PillToggle**

In `frontend/app/workbench/components/page.tsx`:

1. Update the lucide-react import on line 4 — remove `Box` since PillToggle renders the icons internally. Keep the other icons:

```tsx
import { Package, Search, Plus, Settings, Trash2 } from "lucide-react";
```

2. Add imports after the lucide-react import:

```tsx
import { Package as PackageIcon, Box } from "lucide-react";
import { PillToggle, type PillToggleOption } from "@/components/ui/PillToggle";
```

Wait — `Package` is already imported and used for both the toggle icon and the heading icon (line 114) and the empty-state icon (line 175). Keep `Package` in the main import and use it for the heading/empty-state. For the `PillToggle` options, just reference it directly.

Simpler approach — add only the new imports:

```tsx
import { PillToggle, type PillToggleOption } from "@/components/ui/PillToggle";
```

`Package` and `Box` stay in the existing lucide-react import since `Package` is also used elsewhere in the file (heading, empty state).

3. Add the options constant inside the component function, just after the state declarations (after line 51):

```tsx
  const viewOptions: PillToggleOption<View>[] = [
    { value: "library", label: "Library", icon: Package },
    { value: "construction", label: "Construction Parts", icon: Box },
  ];
```

4. Replace lines 67-92 (the toggle JSX inside the `<WorkbenchTwoPanel>`):

Current:

```tsx
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 rounded-full border border-border bg-card p-1">
            <button
              onClick={() => setView("library")}
              className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px] ${
                view === "library"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Package size={12} />
              Library
            </button>
            <button
              onClick={() => setView("construction")}
              className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px] ${
                view === "construction"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Box size={12} />
              Construction Parts
            </button>
          </div>
        </div>
```

Replace with:

```tsx
        <PillToggle options={viewOptions} value={view} onChange={setView} />
```

- [ ] **Step 2: Run all frontend unit tests**

Run: `cd frontend && npx vitest run`
Expected: ALL PASS — identical behavior, ComponentsPage tests still green.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/workbench/components/page.tsx
git commit -m "refactor(gh-405): retrofit Components tab to use PillToggle"
```

---

### Task 5: Retrofit Construction Plans Tab

**Files:**
- Modify: `frontend/app/workbench/construction-plans/page.tsx`

- [ ] **Step 1: Replace ModeButton with PillToggle**

In `frontend/app/workbench/construction-plans/page.tsx`:

1. Add import (near the top, with other component imports):

```tsx
import { PillToggle, type PillToggleOption } from "@/components/ui/PillToggle";
```

2. Add the options constant inside the component function, near the other derived values (after line 512):

```tsx
  const viewModeOptions: PillToggleOption<"plans" | "templates">[] = [
    { value: "plans", label: "Plans", icon: Hammer },
    { value: "templates", label: "Templates", icon: BookTemplate },
  ];
```

3. Delete the entire `ModeButton` function (lines 514-531):

```tsx
  function ModeButton({
    mode,
    Icon,
    label,
  }: Readonly<{ mode: "plans" | "templates"; Icon: typeof Hammer; label: string }>) {
    return (
      <button
        onClick={() => setViewMode(mode)}
        className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px] ${
          viewMode === mode
            ? "bg-primary text-primary-foreground"
            : "text-muted-foreground hover:text-foreground"
        }`}
      >
        <Icon size={12} /> {label}
      </button>
    );
  }
```

4. Replace lines 555-560 (the toggle container):

Current:

```tsx
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 rounded-full border border-border bg-card p-1">
                <ModeButton mode="plans" Icon={Hammer} label="Plans" />
                <ModeButton mode="templates" Icon={BookTemplate} label="Templates" />
              </div>
            </div>
```

Replace with:

```tsx
            <PillToggle options={viewModeOptions} value={viewMode} onChange={setViewMode} />
```

- [ ] **Step 2: Run all frontend unit tests**

Run: `cd frontend && npx vitest run`
Expected: ALL PASS — ConstructionPlansPage tests still find "Templates" and "Plans" text.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/workbench/construction-plans/page.tsx
git commit -m "refactor(gh-405): retrofit Construction Plans tab to use PillToggle"
```

---

### Task 6: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Run full frontend unit test suite**

Run: `cd frontend && npx vitest run`
Expected: ALL PASS — all 42+ test files, 346+ tests green.

- [ ] **Step 2: Run dependency check**

Run: `cd frontend && npm run deps:check`
Expected: PASS — no circular dependencies introduced.

- [ ] **Step 3: Run TypeScript type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS — no type errors.

- [ ] **Step 4: Final commit if any cleanup needed, then push**

```bash
git push origin chore/gh-405-ui-pattern-toggle-header
```
