# eslint-plugin-sonarjs Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install eslint-plugin-sonarjs, fix all existing violations, and add Husky pre-commit hook to enforce linting on every commit.

**Architecture:** Add sonarjs recommended ruleset to existing ESLint flat config. Fix ~31 violations across 15 files. Install Husky + lint-staged in `frontend/` with subdirectory-aware setup.

**Tech Stack:** eslint-plugin-sonarjs, husky, lint-staged, ESLint 9 flat config

**Worktree:** `/Users/szymanski/Projects/da3Dalus/cad-modelling-service.worktrees/gh-377`
**Branch:** `chore/gh-377-eslint-plugin-sonarjs`

---

### Task 1: Install eslint-plugin-sonarjs and update ESLint config

**Files:**
- Modify: `frontend/package.json` (add devDependency)
- Modify: `frontend/eslint.config.mjs` (add sonarjs preset + rule overrides)

- [ ] **Step 1: Install eslint-plugin-sonarjs**

```bash
cd frontend && npm install --save-dev eslint-plugin-sonarjs
```

- [ ] **Step 2: Update eslint.config.mjs**

Replace the entire file with:

```javascript
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import sonarjs from "eslint-plugin-sonarjs";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  sonarjs.configs.recommended,
  {
    rules: {
      "sonarjs/no-clear-text-protocols": "off",
      "sonarjs/publicly-writable-directories": "off",
    },
  },
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "coverage/**",
  ]),
]);

export default eslintConfig;
```

- [ ] **Step 3: Run eslint to verify config loads and see violations**

```bash
cd frontend && npx eslint . 2>&1 | grep "sonarjs/" | wc -l
```

Expected: ~31 sonarjs errors. This is the RED state.

- [ ] **Step 4: Commit config changes**

```bash
git add frontend/package.json frontend/package-lock.json frontend/eslint.config.mjs
git commit -m "chore(gh-377): add eslint-plugin-sonarjs to ESLint config"
```

---

### Task 2: Fix test file violations — unused vars, imports, void-use, readonly

**Files:**
- Modify: `frontend/__tests__/ComponentTreeWeightDisplay.test.tsx:303` (void-use)
- Modify: `frontend/__tests__/ComponentsPage.test.tsx:138` (unused cancelBtn)
- Modify: `frontend/__tests__/FuselageXSecFormSave.test.tsx:6` (unused fireEvent import)
- Modify: `frontend/__tests__/ConstructionPlansPage.test.tsx:183-185` (public-static-readonly)

- [ ] **Step 1: Fix void-use in ComponentTreeWeightDisplay.test.tsx**

At line 303, remove the `void container;` line. Check if `container` is actually used elsewhere in the test — if it's only used in the `render()` destructuring and not referenced after, also remove it from the destructuring.

- [ ] **Step 2: Fix unused cancelBtn in ComponentsPage.test.tsx**

At line 138, delete the line:
```typescript
const cancelBtn = editDialog?.querySelector("button");
```

The variable is never used — `cancelButton` (line 141) is the one that gets clicked.

- [ ] **Step 3: Fix unused fireEvent import in FuselageXSecFormSave.test.tsx**

At line 6, change:
```typescript
import { render, screen, act, fireEvent } from "@testing-library/react";
```
to:
```typescript
import { render, screen, act } from "@testing-library/react";
```

- [ ] **Step 4: Fix public-static-readonly in ConstructionPlansPage.test.tsx**

At lines 183-185, add `readonly` to the static properties:

```typescript
class FakeEventSource {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;
```

- [ ] **Step 5: Run tests to ensure no regressions**

```bash
cd frontend && npm run test:unit -- --run 2>&1 | tail -20
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/__tests__/ComponentTreeWeightDisplay.test.tsx \
       frontend/__tests__/ComponentsPage.test.tsx \
       frontend/__tests__/FuselageXSecFormSave.test.tsx \
       frontend/__tests__/ConstructionPlansPage.test.tsx
git commit -m "fix(gh-377): fix sonarjs violations in test files"
```

---

### Task 3: Fix e2e step file and production code unused vars

**Files:**
- Modify: `frontend/e2e/steps/common.steps.ts:43` (unused firstAeroplane)
- Modify: `frontend/e2e/steps/construction.steps.ts:270` (unused placeholder)
- Modify: `frontend/app/workbench/page.tsx:22` (unused setAeroplaneId)
- Modify: `frontend/lib/planTreeUtils.ts:186,208,271` (unused destructured vars)

- [ ] **Step 1: Fix unused firstAeroplane in common.steps.ts**

At line 43, delete the declaration and its closing line. The variable `firstAeroplane` is declared but `aeroplaneButtons` is used instead. Remove lines 43-45:

```typescript
    const firstAeroplane = page.locator(
      'button:has-text("") >> nth=0',
    );
```

- [ ] **Step 2: Fix unused placeholder in construction.steps.ts**

At line 270, inside the `waitForFunction` callback, remove the unused variable:

```typescript
// Before:
const placeholder = document.querySelector('[class*="items-center"]');
const hasPlaceholder = !!document.body.innerText.includes("Run an analysis to see results");

// After:
const hasPlaceholder = !!document.body.innerText.includes("Run an analysis to see results");
```

- [ ] **Step 3: Fix unused setAeroplaneId in page.tsx**

At line 22, remove `setAeroplaneId` from the destructuring:

```typescript
// Before:
const {
  aeroplaneId, setAeroplaneId,

// After:
const {
  aeroplaneId,
```

- [ ] **Step 4: Fix unused destructured vars in planTreeUtils.ts**

Three locations need fixing:

**Line 186** — `childSuccessors` and `_creatorIdDirty` are unused in the destructuring:
```typescript
// Before:
const { $TYPE, creator_id, successors: childSuccessors, _creatorIdDirty, ...creatorParams } = child;

// After:
const { $TYPE, creator_id, successors: _childSuccessors, _creatorIdDirty: _dirty, ...creatorParams } = child;
```

Wait — if they're unused, we should use rest-property to exclude them. Since `$TYPE` and `creator_id` are used, and `creatorParams` captures the rest, we only need to exclude `successors` and `_creatorIdDirty`. They're already being excluded by destructuring into named vars. The sonarjs rule wants them prefixed with `_` or removed.

Correct fix:
```typescript
const { $TYPE, creator_id, successors: _successors, _creatorIdDirty: _dirty, ...creatorParams } = child;
```

**Line 208** — `_s` and `_d` are already underscore-prefixed but sonarjs still flags them:
```typescript
// Before:
const { successors: _s, _creatorIdDirty: _d, ...rootFields } = node as Record<string, unknown>;

// After — use Omit-style exclude via rest:
const { successors: _excluded1, _creatorIdDirty: _excluded2, ...rootFields } = node as Record<string, unknown>;
```

Actually, sonarjs/no-unused-vars respects `_` prefix in some versions. Read the actual error — if it still flags `_s`, the simplest fix is an inline disable comment since the destructuring is intentional (stripping fields from the spread):
```typescript
// eslint-disable-next-line sonarjs/no-unused-vars -- destructure-to-exclude
const { successors: _s, _creatorIdDirty: _d, ...rootFields } = node as Record<string, unknown>;
```

**Line 271** — same pattern:
```typescript
// eslint-disable-next-line sonarjs/no-unused-vars -- destructure-to-exclude
const { successors: _s, ...nodeFields } = node as Record<string, unknown>;
```

Read each line to verify the exact code before applying. Use `eslint-disable-next-line` only where the unused var is intentional (destructure-to-exclude pattern).

- [ ] **Step 5: Run eslint on changed files**

```bash
cd frontend && npx eslint app/workbench/page.tsx lib/planTreeUtils.ts e2e/steps/common.steps.ts e2e/steps/construction.steps.ts 2>&1 | grep "sonarjs/"
```

Expected: No sonarjs/no-unused-vars or sonarjs/no-dead-store errors in these files.

- [ ] **Step 6: Run unit tests**

```bash
cd frontend && npm run test:unit -- --run 2>&1 | tail -10
```

- [ ] **Step 7: Commit**

```bash
git add frontend/e2e/steps/common.steps.ts \
       frontend/e2e/steps/construction.steps.ts \
       frontend/app/workbench/page.tsx \
       frontend/lib/planTreeUtils.ts
git commit -m "fix(gh-377): remove unused variables and dead stores"
```

---

### Task 4: Extract resolveParamValue helper and fix nested ternaries in plan files

The nested ternary `typeof val === "string" ? val : typeof val === "number" ? String(val) : \`{${param}}\`` appears in 4 places across 3 files. Extract a shared helper.

**Files:**
- Modify: `frontend/lib/planTreeUtils.ts:310,367` (two occurrences)
- Modify: `frontend/lib/planValidation.ts:73` (one occurrence)
- Modify: `frontend/components/workbench/construction-plans/PlanTreeSection.tsx:35` (one occurrence)

- [ ] **Step 1: Add resolveParamValue to planTreeUtils.ts**

Add this exported function near the top of `planTreeUtils.ts`, after the imports and type definitions:

```typescript
export function resolveParamValue(val: unknown, fallback: string): string {
  if (typeof val === "string") return val;
  if (typeof val === "number") return String(val);
  return fallback;
}
```

- [ ] **Step 2: Replace nested ternary in buildStepNode (planTreeUtils.ts:308-310)**

```typescript
// Before (line 308-310):
node.creator_id = base.replace(/\{(\w+)\}/g, (_match, param) => {
  const val = nodeRecord[param];
  return typeof val === "string" ? val : typeof val === "number" ? String(val) : `{${param}}`;
});

// After:
node.creator_id = base.replace(/\{(\w+)\}/g, (_match, param) =>
  resolveParamValue(nodeRecord[param], `{${param}}`),
);
```

- [ ] **Step 3: Replace nested ternary in resolveNodeShapes (planTreeUtils.ts:365-367)**

```typescript
// Before (line 365-367):
resolved = resolved.replace(/\{(\w+)\}/g, (_match, param) => {
  const val = nodeRecord[param];
  return typeof val === "string" ? val : typeof val === "number" ? String(val) : `{${param}}`;
});

// After:
resolved = resolved.replace(/\{(\w+)\}/g, (_match, param) =>
  resolveParamValue(nodeRecord[param], `{${param}}`),
);
```

- [ ] **Step 4: Replace nested ternary in planValidation.ts:71-73**

Add import at top of file:
```typescript
import { isShapeRefType, resolveParamValue } from "./planTreeUtils";
```

Then fix the ternary:
```typescript
// Before (line 71-73):
resolved = resolved.replace(/\{(\w+)\}/g, (_match, param) => {
  const val = nodeRecord[param];
  return typeof val === "string" ? val : typeof val === "number" ? String(val) : `{${param}}`;
});

// After:
resolved = resolved.replace(/\{(\w+)\}/g, (_match, param) =>
  resolveParamValue(nodeRecord[param], `{${param}}`),
);
```

Note: `isShapeRefType` is already imported from `planTreeUtils` in this file. Verify the existing import and add `resolveParamValue` to it.

- [ ] **Step 5: Replace nested ternary in PlanTreeSection.tsx:33-35**

Add import:
```typescript
import { resolveParamValue } from "@/lib/planTreeUtils";
```

Then fix:
```typescript
// Before (lines 33-35):
const val = nodeRecord[param];
return typeof val === "string" ? val : typeof val === "number" ? String(val) : `{${param}}`;

// After:
return resolveParamValue(nodeRecord[param], `{${param}}`);
```

Remove the now-unnecessary `val` variable declaration inside the callback.

- [ ] **Step 6: Run eslint on changed files**

```bash
cd frontend && npx eslint lib/planTreeUtils.ts lib/planValidation.ts components/workbench/construction-plans/PlanTreeSection.tsx 2>&1 | grep "sonarjs/"
```

Expected: No sonarjs/no-nested-conditional errors in these files.

- [ ] **Step 7: Run unit tests**

```bash
cd frontend && npm run test:unit -- --run 2>&1 | tail -10
```

- [ ] **Step 8: Commit**

```bash
git add frontend/lib/planTreeUtils.ts \
       frontend/lib/planValidation.ts \
       frontend/components/workbench/construction-plans/PlanTreeSection.tsx
git commit -m "refactor(gh-377): extract resolveParamValue helper to fix nested ternaries"
```

---

### Task 5: Fix remaining nested ternaries in UI components and tests

**Files:**
- Modify: `frontend/app/workbench/page.tsx:42-46`
- Modify: `frontend/app/workbench/construction-plans/page.tsx:205`
- Modify: `frontend/components/workbench/AvlGeometryEditor.tsx:189-193`
- Modify: `frontend/components/workbench/SimpleTreeRow.tsx:94`
- Modify: `frontend/__tests__/ConstructionPlansPage.test.tsx:78`

- [ ] **Step 1: Fix nested ternary in page.tsx:42-46**

```typescript
// Before:
const paginatorTotal = mode === "fuselage"
  ? fuselage?.x_secs?.length
  : mode === "wingconfig"
    ? wingConfig?.segments?.length
    : wing?.x_secs?.length;

// After — use a lookup or function:
function getPaginatorTotal() {
  if (mode === "fuselage") return fuselage?.x_secs?.length;
  if (mode === "wingconfig") return wingConfig?.segments?.length;
  return wing?.x_secs?.length;
}
const paginatorTotal = getPaginatorTotal();
```

Since this is inside a React component, use a plain function declared before the assignment (or `useMemo` if the computation is expensive — it's not here, so a function is fine).

- [ ] **Step 2: Fix nested ternary in construction-plans/page.tsx:205**

```typescript
// Before:
const detail = isTemplate ? templateDetail : (activePlanDetail?.id === planId ? activePlanDetail : null);

// After:
let detail = null;
if (isTemplate) {
  detail = templateDetail;
} else if (activePlanDetail?.id === planId) {
  detail = activePlanDetail;
}
```

- [ ] **Step 3: Fix nested ternary in AvlGeometryEditor.tsx:189-193**

This is JSX conditional rendering (`isLoading ? ... : mode === "diff" ? ... : ...`). Refactor into an early-determined variable:

```typescript
// Before the return statement, compute the editor content:
const editorContent = geometry.isLoading ? (
  <div className="flex h-full items-center justify-center text-[13px] text-muted-foreground">
    Loading AVL geometry…
  </div>
) : mode === "diff" && regeneratedContent !== null ? (
  <MonacoDiffEditor ... />
) : (
  <MonacoEditor ... />
);

// Then in JSX:
{/* Editor Body */}
<div className="flex-1 overflow-hidden">
  {editorContent}
</div>
```

Actually, the simplest compliant fix is to extract the nested part into a helper:

```typescript
function renderEditor() {
  if (geometry.isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-[13px] text-muted-foreground">
        Loading AVL geometry…
      </div>
    );
  }
  if (mode === "diff" && regeneratedContent !== null) {
    return <MonacoDiffEditor ... />;
  }
  return <MonacoEditor ... />;
}
```

Read the full JSX to get the exact props for MonacoDiffEditor and MonacoEditor. Place the function inside the component before the return.

- [ ] **Step 4: Fix nested ternary in SimpleTreeRow.tsx:94**

```typescript
// Before (line 94):
className={`whitespace-nowrap ${node.error ? "text-[12px] text-red-400/70" : node.muted ? "text-[12px] text-muted-foreground" : "font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"}`}

// After — extract a function:
const labelClass = (() => {
  if (node.error) return "text-[12px] text-red-400/70";
  if (node.muted) return "text-[12px] text-muted-foreground";
  return "font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground";
})();

// Then:
<span className={`whitespace-nowrap ${labelClass}`}>
```

- [ ] **Step 5: Fix nested ternary in ConstructionPlansPage.test.tsx:78**

This is in mock data — a large ternary choosing mock responses by `id`. Refactor into a `Map` or `switch`:

```typescript
// Before: id === 1 ? {...} : id === 2 ? {...} : {...}
// After: use a lookup object

const mockPlans: Record<number, Plan> = {
  1: { id: 1, name: "Wing Template", ... },
  2: { id: 2, name: "eHawk Build", ... },
};
// In the mock handler:
return mockPlans[id] ?? null;
```

Read the full mock to get exact shapes. The key is eliminating the nested `id === 1 ? ... : id === 2 ? ...` chain.

- [ ] **Step 6: Run eslint on changed files**

```bash
cd frontend && npx eslint app/workbench/page.tsx app/workbench/construction-plans/page.tsx components/workbench/AvlGeometryEditor.tsx components/workbench/SimpleTreeRow.tsx __tests__/ConstructionPlansPage.test.tsx 2>&1 | grep "sonarjs/no-nested-conditional"
```

Expected: Zero results.

- [ ] **Step 7: Run unit tests**

```bash
cd frontend && npm run test:unit -- --run 2>&1 | tail -10
```

- [ ] **Step 8: Commit**

```bash
git add frontend/app/workbench/page.tsx \
       frontend/app/workbench/construction-plans/page.tsx \
       frontend/components/workbench/AvlGeometryEditor.tsx \
       frontend/components/workbench/SimpleTreeRow.tsx \
       frontend/__tests__/ConstructionPlansPage.test.tsx
git commit -m "refactor(gh-377): eliminate nested ternaries in UI components and tests"
```

---

### Task 6: Fix cognitive complexity violations

**Files:**
- Modify: `frontend/app/workbench/construction-plans/page.tsx:428` (handleDragEnd — complexity 17)
- Modify: `frontend/lib/planValidation.ts:22` (validateNode — complexity 20)
- Modify: `frontend/lib/planTreeUtils.ts:332` (resolveNodeShapes — complexity 23)

- [ ] **Step 1: Reduce complexity of handleDragEnd (construction-plans/page.tsx:428)**

Extract the drop-target parsing into a helper function:

```typescript
function parseDropTarget(overId: string): { planId: number; path: string } | null {
  if (overId.startsWith("plan-root-")) {
    return { planId: Number(overId.slice("plan-root-".length)), path: "root" };
  }
  if (overId.startsWith("node-plan-")) {
    const rest = overId.slice("node-plan-".length);
    const dotIdx = rest.indexOf("-");
    if (dotIdx > 0) {
      return { planId: Number(rest.slice(0, dotIdx)), path: rest.slice(dotIdx + 1) };
    }
  }
  return null;
}
```

Place this function **outside** the component (it's pure, no dependencies on component state). Then simplify handleDragEnd:

```typescript
const handleDragEnd = useCallback(
  async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;
    const activeId = String(active.id);
    if (!activeId.startsWith("creator-")) return;

    const creator = active.data.current?.creator as CreatorInfo | undefined;
    if (!creator) return;

    const target = parseDropTarget(String(over.id));
    if (!target) return;

    try {
      await addCreatorToPlan(target.planId, target.path, creator);
    } catch (err) {
      alert(`Drop failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  },
  [addCreatorToPlan],
);
```

- [ ] **Step 2: Reduce complexity of validateNode (planValidation.ts:22)**

Extract the shape-reference check into a helper:

```typescript
function checkShapeRefs(
  val: unknown,
  paramName: string,
  availableShapes: Set<string>,
  path: string,
  creatorId: string,
  issues: ValidationIssue[],
): void {
  const refs = Array.isArray(val) ? val.map(String) : [String(val)];
  for (const ref of refs) {
    if (ref.trim() && !availableShapes.has(ref)) {
      issues.push({
        path,
        creatorId,
        message: `Shape reference "${ref}" (${paramName}) is not available at this point`,
      });
    }
  }
}
```

Then in validateNode, replace lines 51-62:
```typescript
if (isShapeRefType(param.type) && !isEmpty(val)) {
  checkShapeRefs(val, param.name, availableShapes, path, node.creator_id, issues);
}
```

- [ ] **Step 3: Reduce complexity of resolveNodeShapes (planTreeUtils.ts:332)**

Extract the input-building logic for a single parameter into a helper:

```typescript
function collectParamInputs(
  param: CreatorParam,
  val: unknown,
): ResolvedShapeInput[] {
  if (param.type === "list[ShapeId]" && Array.isArray(val)) {
    if (val.length === 0) return [{ paramName: param.name, boundValue: null }];
    return val.map((v) => ({
      paramName: param.name,
      boundValue: typeof v === "string" && v.trim() !== "" ? v : null,
    }));
  }
  const bound = typeof val === "string" && val.trim() !== "" ? val : null;
  return [{ paramName: param.name, boundValue: bound }];
}
```

Then in resolveNodeShapes, replace the loop body:
```typescript
const inputs: ResolvedShapeInput[] = [];
for (const p of info.parameters) {
  if (!isShapeRefType(p.type)) continue;
  const val = (node as Record<string, unknown>)[p.name];
  inputs.push(...collectParamInputs(p, val));
}
```

- [ ] **Step 4: Run eslint on changed files**

```bash
cd frontend && npx eslint app/workbench/construction-plans/page.tsx lib/planValidation.ts lib/planTreeUtils.ts 2>&1 | grep "sonarjs/cognitive-complexity"
```

Expected: Zero results.

- [ ] **Step 5: Run unit tests**

```bash
cd frontend && npm run test:unit -- --run 2>&1 | tail -10
```

- [ ] **Step 6: Commit**

```bash
git add frontend/app/workbench/construction-plans/page.tsx \
       frontend/lib/planValidation.ts \
       frontend/lib/planTreeUtils.ts
git commit -m "refactor(gh-377): extract helpers to reduce cognitive complexity"
```

---

### Task 7: Fix slow-regex violations

**Files:**
- Modify: `frontend/components/workbench/avlLanguage.ts:29,34` (two regexes in Monaco tokenizer)
- Modify: `frontend/components/workbench/AnalysisViewerPanel.tsx:252` (YDUP regex)

- [ ] **Step 1: Fix slow-regex in avlLanguage.ts**

**Line 29** — `/[!#].*$/` — `.*$` can backtrack. Fix by being explicit:
```typescript
// Before:
[/[!#].*$/, "comment"],
// After:
[/[!#][^\n]*/, "comment"],
```

**Line 34** — `/-?\d+\.?\d*([eE][+-]?\d+)?/` — `\d+` and `\d*` overlap causing backtracking. Fix by grouping the decimal part:
```typescript
// Before:
[/-?\d+\.?\d*([eE][+-]?\d+)?/, "number"],
// After:
[/-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?/, "number"],
```

- [ ] **Step 2: Fix slow-regex in AnalysisViewerPanel.tsx:252**

```typescript
// Before:
const baseName = surface.surface_name.replace(/\s*\(YDUP\)$/, "");
// After — use string methods instead of regex:
const baseName = surface.surface_name.endsWith("(YDUP)")
  ? surface.surface_name.slice(0, -6).trimEnd()
  : surface.surface_name;
```

`"(YDUP)".length === 6`. `trimEnd()` removes any trailing whitespace that was before `(YDUP)`.

- [ ] **Step 3: Run eslint on changed files**

```bash
cd frontend && npx eslint components/workbench/avlLanguage.ts components/workbench/AnalysisViewerPanel.tsx 2>&1 | grep "sonarjs/slow-regex"
```

Expected: Zero results.

- [ ] **Step 4: Run unit tests**

```bash
cd frontend && npm run test:unit -- --run 2>&1 | tail -10
```

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/avlLanguage.ts \
       frontend/components/workbench/AnalysisViewerPanel.tsx
git commit -m "fix(gh-377): rewrite slow regexes to avoid backtracking"
```

---

### Task 8: Install Husky + lint-staged and create pre-commit hook

**Files:**
- Modify: `frontend/package.json` (add devDeps, prepare script, lint-staged config)
- Create: `frontend/.husky/pre-commit`

- [ ] **Step 1: Install husky and lint-staged**

```bash
cd frontend && npm install --save-dev husky lint-staged
```

- [ ] **Step 2: Add prepare script and lint-staged config to package.json**

In `frontend/package.json`, add to `"scripts"`:
```json
"prepare": "cd .. && husky frontend/.husky"
```

Add top-level:
```json
"lint-staged": {
  "*.{ts,tsx,js,jsx}": "eslint --max-warnings=0"
}
```

- [ ] **Step 3: Create pre-commit hook**

```bash
mkdir -p frontend/.husky
cat > frontend/.husky/pre-commit << 'EOF'
cd frontend && npx lint-staged
EOF
```

- [ ] **Step 4: Run prepare to install the hook**

```bash
cd frontend && npm run prepare
```

Expected: Husky installs the git hook successfully.

- [ ] **Step 5: Verify hook is installed**

```bash
cat .git/hooks/pre-commit 2>/dev/null || cat ../.git/hooks/pre-commit 2>/dev/null
```

The file should exist and reference the husky hook runner.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/.husky/pre-commit
git commit -m "chore(gh-377): add Husky pre-commit hook with lint-staged"
```

This commit itself will trigger the new pre-commit hook — if it passes, the hook is working.

---

### Task 9: Final verification — clean lint + passing tests

- [ ] **Step 1: Run full eslint**

```bash
cd frontend && npx eslint . 2>&1 | grep "sonarjs/"
```

Expected: **Zero sonarjs errors.** There may be pre-existing warnings from other rules (react-hooks, typescript-eslint) — those are out of scope.

- [ ] **Step 2: Run full unit test suite**

```bash
cd frontend && npm run test:unit -- --run
```

Expected: All tests pass.

- [ ] **Step 3: Run npm run lint (the standard command)**

```bash
cd frontend && npm run lint
```

Expected: Exits cleanly (exit code 0) or shows only pre-existing warnings.

- [ ] **Step 4: Verify lint count**

```bash
cd frontend && npx eslint . 2>&1 | grep -c "error"
```

Expected: 0 errors. Any errors mean a violation was missed — go back and fix.
