# userEvent Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all `fireEvent` calls with `@testing-library/user-event` across 22 frontend test files to eliminate CI `act()` warnings.

**Architecture:** Mechanical transform — no production code changes. Install userEvent, then convert each file following the pattern table. Tests must remain green after each batch.

**Tech Stack:** `@testing-library/user-event@^14`, vitest, React Testing Library

---

### Task 1: Install @testing-library/user-event

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install the package**

```bash
cd frontend && npm install --save-dev @testing-library/user-event@^14
```

- [ ] **Step 2: Verify installation**

```bash
grep "user-event" frontend/package.json
```

Expected: `"@testing-library/user-event": "^14.x.x"` in devDependencies

- [ ] **Step 3: Run tests to confirm no regressions**

```bash
cd frontend && npm run test:unit -- --run
```

Expected: 346 tests pass

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(gh-348): install @testing-library/user-event@^14"
```

---

### Task 2: Batch 1 — simple click-only files (8 files, ~29 calls)

**Files:**
- Modify: `frontend/__tests__/SplitHandle.test.tsx` (1 call)
- Modify: `frontend/__tests__/ComponentTreeWeightDisplay.test.tsx` (1 call)
- Modify: `frontend/__tests__/UnsavedChangesModal.test.tsx` (3 calls)
- Modify: `frontend/__tests__/CotsPickerDialog.test.tsx` (2 calls)
- Modify: `frontend/__tests__/ComponentsPage.test.tsx` (3 calls)
- Modify: `frontend/__tests__/ComponentTypeManagementDialog.test.tsx` (3 calls)
- Modify: `frontend/__tests__/FuselageTree.test.tsx` (6 calls)
- Modify: `frontend/__tests__/ComponentTreeConstructionPartFlow.test.tsx` (6 calls)

**Transform pattern for each file:**

1. Replace `import { ..., fireEvent, ... } from "@testing-library/react"` — remove `fireEvent` from the import. Add `import userEvent from "@testing-library/user-event"`.
2. Add `const user = userEvent.setup();` at the start of each test (or in a `beforeEach` if many tests share setup).
3. Replace `fireEvent.click(el)` → `await user.click(el)`.
4. Make test functions `async` if not already: `it("...", async () => { ... })`.

- [ ] **Step 1: Transform all 8 files**

Apply the pattern above to each file. Each file is click-only so only `fireEvent.click` → `await user.click` is needed.

- [ ] **Step 2: Run tests**

```bash
cd frontend && npm run test:unit -- --run
```

Expected: 346 tests pass, zero `fireEvent` in these 8 files.

- [ ] **Step 3: Verify no fireEvent remains**

```bash
grep -l "fireEvent" frontend/__tests__/SplitHandle.test.tsx frontend/__tests__/ComponentTreeWeightDisplay.test.tsx frontend/__tests__/UnsavedChangesModal.test.tsx frontend/__tests__/CotsPickerDialog.test.tsx frontend/__tests__/ComponentsPage.test.tsx frontend/__tests__/ComponentTypeManagementDialog.test.tsx frontend/__tests__/FuselageTree.test.tsx frontend/__tests__/ComponentTreeConstructionPartFlow.test.tsx
```

Expected: no output (all clean).

- [ ] **Step 4: Commit**

```bash
git add frontend/__tests__/SplitHandle.test.tsx frontend/__tests__/ComponentTreeWeightDisplay.test.tsx frontend/__tests__/UnsavedChangesModal.test.tsx frontend/__tests__/CotsPickerDialog.test.tsx frontend/__tests__/ComponentsPage.test.tsx frontend/__tests__/ComponentTypeManagementDialog.test.tsx frontend/__tests__/FuselageTree.test.tsx frontend/__tests__/ComponentTreeConstructionPartFlow.test.tsx
git commit -m "chore(gh-348): migrate batch 1 (8 click-only files) to userEvent"
```

---

### Task 3: Batch 2 — click + change files (8 files, ~44 calls)

**Files:**
- Modify: `frontend/__tests__/ConstructionPartPickerDialog.test.tsx` (3 calls)
- Modify: `frontend/__tests__/CreatorGallery.test.tsx` (3 calls)
- Modify: `frontend/__tests__/PropertyEditDialog.test.tsx` (6 calls)
- Modify: `frontend/__tests__/GroupAddMenu.test.tsx` (5 calls)
- Modify: `frontend/__tests__/NodePropertyPanel.test.tsx` (10 calls)
- Modify: `frontend/__tests__/ConstructionPartsGrid.test.tsx` (4 calls)
- Modify: `frontend/__tests__/ConstructionPlansPage.test.tsx` (10 calls)
- Modify: `frontend/__tests__/XsecTreeCrud.test.tsx` (3 calls — added after issue creation)

**Additional transform patterns (beyond click):**

- `fireEvent.change(input, { target: { value: "x" } })` → `await user.clear(input); await user.type(input, "x")`.
- `fireEvent.change(select, { target: { value: "v" } })` (for `<select>` elements) → `await user.selectOptions(select, "v")`.
- `fireEvent.keyDown(el, { key: "Enter" })` → `await user.keyboard("{Enter}")`.
  - Note: `user.keyboard` types on the currently focused element. Ensure the element is focused first (via `user.click` or `el.focus()`).

- [ ] **Step 1: Transform all 8 files**

Apply both click and change/keyDown patterns. Check each `fireEvent.change` to determine if it's an `<input>`, `<select>`, or `<textarea>` and use the appropriate userEvent method.

- [ ] **Step 2: Run tests**

```bash
cd frontend && npm run test:unit -- --run
```

Expected: 346 tests pass.

- [ ] **Step 3: Verify no fireEvent remains**

```bash
grep -l "fireEvent" frontend/__tests__/ConstructionPartPickerDialog.test.tsx frontend/__tests__/CreatorGallery.test.tsx frontend/__tests__/PropertyEditDialog.test.tsx frontend/__tests__/GroupAddMenu.test.tsx frontend/__tests__/NodePropertyPanel.test.tsx frontend/__tests__/ConstructionPartsGrid.test.tsx frontend/__tests__/ConstructionPlansPage.test.tsx frontend/__tests__/XsecTreeCrud.test.tsx
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add frontend/__tests__/ConstructionPartPickerDialog.test.tsx frontend/__tests__/CreatorGallery.test.tsx frontend/__tests__/PropertyEditDialog.test.tsx frontend/__tests__/GroupAddMenu.test.tsx frontend/__tests__/NodePropertyPanel.test.tsx frontend/__tests__/ConstructionPartsGrid.test.tsx frontend/__tests__/ConstructionPlansPage.test.tsx frontend/__tests__/XsecTreeCrud.test.tsx
git commit -m "chore(gh-348): migrate batch 2 (8 click+change files) to userEvent"
```

---

### Task 4: Batch 3a — medium-complexity files (3 files, ~34 calls)

**Files:**
- Modify: `frontend/__tests__/ComponentEditDialogDynamic.test.tsx` (14 calls)
- Modify: `frontend/__tests__/ComponentTreeAddFlow.test.tsx` (18 calls)
- Modify: `frontend/__tests__/SegmentPaginator.test.tsx` (5 calls — added after issue creation)

These files have mixed click/change patterns but no special handling (no file inputs, no flushMicrotasks).

- [ ] **Step 1: Transform all 3 files**

Same patterns as Task 3. Pay attention to `fireEvent.change` on `<select>` elements — use `user.selectOptions`.

- [ ] **Step 2: Run tests**

```bash
cd frontend && npm run test:unit -- --run
```

Expected: 346 tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/__tests__/ComponentEditDialogDynamic.test.tsx frontend/__tests__/ComponentTreeAddFlow.test.tsx frontend/__tests__/SegmentPaginator.test.tsx
git commit -m "chore(gh-348): migrate batch 3a (3 mixed files) to userEvent"
```

---

### Task 5: Batch 3b — EditParamsModal (9 calls, added after issue creation)

**Files:**
- Modify: `frontend/__tests__/EditParamsModal.test.tsx` (9 calls)

This file was added after the issue was created. Standard click + change transforms.

- [ ] **Step 1: Transform the file**

Same patterns as previous tasks.

- [ ] **Step 2: Run tests**

```bash
cd frontend && npm run test:unit -- --run
```

- [ ] **Step 3: Commit**

```bash
git add frontend/__tests__/EditParamsModal.test.tsx
git commit -m "chore(gh-348): migrate EditParamsModal to userEvent"
```

---

### Task 6: ConstructionPartUploadDialog — file input handling (11 calls)

**Files:**
- Modify: `frontend/__tests__/ConstructionPartUploadDialog.test.tsx`

**Special handling:** 6 of the 11 `fireEvent.change` calls simulate file selection on `<input type="file">`. These must use `user.upload()`:

```typescript
// Before:
fireEvent.change(fileInput, { target: { files: [file] } });

// After:
await user.upload(fileInput, file);
```

The `file` variable must be a proper `File` object (not just `{ name: "..." }`). Check if existing tests already construct `File` objects; if not, create them:

```typescript
const file = new File(["content"], "part.step", { type: "application/step" });
```

- [ ] **Step 1: Transform the file**

Replace all `fireEvent.click` → `await user.click` and all file-input `fireEvent.change` → `await user.upload`. Convert non-file `fireEvent.change` with standard patterns.

- [ ] **Step 2: Run tests**

```bash
cd frontend && npm run test:unit -- --run
```

- [ ] **Step 3: Commit**

```bash
git add frontend/__tests__/ConstructionPartUploadDialog.test.tsx
git commit -m "chore(gh-348): migrate ConstructionPartUploadDialog to userEvent.upload"
```

---

### Task 7: ComponentTypeCreateFlow — flushMicrotasks removal (79 calls)

**Files:**
- Modify: `frontend/__tests__/ComponentTypeCreateFlow.test.tsx`

**Special handling:**

1. **Remove `flushMicrotasks()` helper** (lines 76-79) and all 11 call sites. With `userEvent`, state updates settle before `await` resolves.

2. **Convert `clickSave()` helper** (line 69) to async:
   ```typescript
   // Before:
   const clickSave = () => fireEvent.click(screen.getByRole("button", { name: /save/i }));
   
   // After:
   const clickSave = async () => await user.click(screen.getByRole("button", { name: /save/i }));
   ```
   All call sites must add `await`: `clickSave()` → `await clickSave()`.

3. **Convert `editableTextInputs()` helper** (line 61) if it uses fireEvent — make async if needed.

4. **Standard transforms** for all remaining `fireEvent.click` and `fireEvent.change` calls.

This is the largest and most complex file (79 calls). Take extra care with the `await` chain — missing a single `await` can cause flaky tests.

- [ ] **Step 1: Transform the file**

Remove flushMicrotasks, convert helpers, transform all fireEvent calls.

- [ ] **Step 2: Run tests**

```bash
cd frontend && npm run test:unit -- --run
```

- [ ] **Step 3: Verify zero fireEvent and zero flushMicrotasks**

```bash
grep -c "fireEvent\|flushMicrotasks" frontend/__tests__/ComponentTypeCreateFlow.test.tsx
```

Expected: 0

- [ ] **Step 4: Commit**

```bash
git add frontend/__tests__/ComponentTypeCreateFlow.test.tsx
git commit -m "chore(gh-348): migrate ComponentTypeCreateFlow to userEvent, remove flushMicrotasks"
```

---

### Task 8: Final verification and cleanup

- [ ] **Step 1: Verify zero fireEvent across all test files**

```bash
grep -r "fireEvent" frontend/__tests__/ --include="*.tsx" --include="*.ts" -l
```

Expected: no output.

- [ ] **Step 2: Run full test suite**

```bash
cd frontend && npm run test:unit -- --run
```

Expected: 346 tests pass, zero `act()` warnings in output.

- [ ] **Step 3: Verify no production code changes**

```bash
git diff --name-only HEAD~7 | grep -v "__tests__/" | grep -v "package"
```

Expected: no output (only test files and package.json/lock changed).

- [ ] **Step 4: Create PR**

```bash
gh pr create --title "chore(gh-348): migrate frontend tests from fireEvent to userEvent" --body "..."
```
