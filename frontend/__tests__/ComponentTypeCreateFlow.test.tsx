/**
 * End-to-end integration test for the Manage Types → New Type → Save flow.
 *
 * Reproduces the bug reported 2026-04-16: clicking Save in the "New Type"
 * dialog does nothing (no network request, no dialog close). The test fails
 * before the fix and passes after.
 *
 * Exercises the real ComponentTypeManagementDialog + ComponentTypeEditDialog
 * together (no mocks for the child). Only the SWR hook and the CRUD client
 * functions are stubbed so the test drives the UI deterministically.
 *
 * The file is also the regression suite for the 2026-04-16 delete-cascade
 * incident: it pins down the expected payloads for every mutation the user
 * can perform through the Manage-Types surface, so the UI can't silently
 * start firing bogus requests again.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within, waitFor } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    X: icon, Plus: icon, Pencil: icon, Trash2: icon, Lock: icon,
    Loader2: icon, Check: icon, Settings: icon,
  };
});

const mockCreate = vi.fn().mockResolvedValue({ id: 999, name: "new_type" });
const mockUpdate = vi.fn().mockResolvedValue({});
const mockDelete = vi.fn().mockResolvedValue(undefined);
const mockMutate = vi.fn();

// Variable bag so individual tests can change what the hook returns before
// rendering (e.g. to test the "edit existing type" path).
let hookReturn: {
  types: Array<Record<string, unknown>>;
  isLoading: boolean;
  mutate: () => void;
  error: Error | null;
} = { types: [], isLoading: false, mutate: mockMutate, error: null };

vi.mock("@/hooks/useComponentTypes", () => ({
  useComponentTypes: () => hookReturn,
  createComponentType: (...a: unknown[]) => mockCreate(...a),
  updateComponentType: (...a: unknown[]) => mockUpdate(...a),
  deleteComponentType: (...a: unknown[]) => mockDelete(...a),
}));

vi.mock("@/lib/fetcher", () => ({ API_BASE: "http://x", fetcher: vi.fn() }));

import { ComponentTypeManagementDialog } from "@/components/workbench/ComponentTypeManagementDialog";

beforeEach(() => {
  vi.clearAllMocks();
  hookReturn = { types: [], isLoading: false, mutate: mockMutate, error: null };
});

/** Grab the editable (non-disabled) text inputs inside the Edit dialog. */
function editableTextInputs(container: HTMLElement): HTMLInputElement[] {
  const all = container.querySelectorAll(
    'input[type="text"]',
  ) as NodeListOf<HTMLInputElement>;
  return Array.from(all).filter((i) => !i.disabled);
}

/** Click the Save button on the currently open dialog. */
function clickSave() {
  const saveButtons = screen.getAllByText(/^Save$/);
  expect(saveButtons.length).toBeGreaterThan(0);
  fireEvent.click(saveButtons[0]);
}

/** Flush two microtask ticks so awaited promises in handlers settle. */
async function flushMicrotasks() {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}

describe("Manage Types → New Type → Save flow (e2e)", () => {
  it("creates a new type end-to-end: open mgmt → click New Type → fill form → Save → createComponentType called", async () => {
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );

    // 1. Click "+ New Type"
    fireEvent.click(screen.getByRole("button", { name: /New Type/i }));

    // 2. Verify Edit dialog opened
    expect(screen.getByText(/New Type:/i)).toBeDefined();

    // 3. Fill in Name + Label
    const editable = editableTextInputs(container);
    fireEvent.change(editable[0], { target: { value: "carbon_tube" } });
    // [name, label, description] — index 1 is label
    fireEvent.change(editable[1], { target: { value: "Carbon Tube" } });

    // 4. Click Save
    clickSave();

    // 5. The backend client must have been called with the payload
    await flushMicrotasks();
    expect(mockCreate).toHaveBeenCalledTimes(1);
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "carbon_tube",
        label: "Carbon Tube",
        schema: [],
      }),
    );
  });

  it("Save with empty Label is blocked — no API call", () => {
    render(<ComponentTypeManagementDialog open={true} onClose={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /New Type/i }));
    // No input → click Save
    clickSave();
    expect(mockCreate).not.toHaveBeenCalled();
    // Inline error appears
    expect(screen.getByText(/Label is required/i)).toBeDefined();
  });

  it("Save with non-snake_case Name is blocked for new types", () => {
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /New Type/i }));

    const editable = editableTextInputs(container);
    fireEvent.change(editable[0], { target: { value: "CarbonTube" } });  // PascalCase
    fireEvent.change(editable[1], { target: { value: "Carbon Tube" } });

    clickSave();

    expect(mockCreate).not.toHaveBeenCalled();
    // The inline error mentions snake_case. The label also mentions it, so we
    // rely on getAllByText.
    expect(screen.getAllByText(/snake_case/i).length).toBeGreaterThanOrEqual(2);
  });

  // ------------------------------------------------------------------- //
  // Extra probes added while debugging the "does not save" bug report.
  // These assertions try to narrow down where exactly the flow breaks
  // in the real browser.
  // ------------------------------------------------------------------- //

  it("after successful save, onSaved is invoked so the list refetches", async () => {
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /New Type/i }));

    const editable = editableTextInputs(container);
    fireEvent.change(editable[0], { target: { value: "t1" } });
    fireEvent.change(editable[1], { target: { value: "T1" } });

    clickSave();
    await flushMicrotasks();

    expect(mockMutate).toHaveBeenCalled();
  });

  it("clicking Save propagates: no event handler outside the dialog triggers before handleSave", () => {
    // Guards against a regression where stopPropagation on the inner card
    // is dropped — which would let the parent backdrop's onClick close the
    // dialog before the async save settles.
    const onClose = vi.fn();
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={onClose} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /New Type/i }));

    const editable = editableTextInputs(container);
    fireEvent.change(editable[0], { target: { value: "t2" } });
    fireEvent.change(editable[1], { target: { value: "T2" } });

    clickSave();
    // The parent Management dialog must NOT have closed as a side-effect of
    // the Save click (Save closes the EDIT dialog via onSaved→onClose, but
    // the Management dialog's onClose must not fire).
    expect(onClose).not.toHaveBeenCalled();
  });
});

// ----------------------------------------------------------------------- //
// Payload contract — what the backend actually sees on every save.
// These tests guard against regressions where the frontend silently starts
// dropping fields or sending stringified JSON (the 2026-04-16 schema bug).
// ----------------------------------------------------------------------- //

describe("Create-Type payload contract", () => {
  it("Description field is included in the payload", async () => {
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /New Type/i }));
    const editable = editableTextInputs(container);
    fireEvent.change(editable[0], { target: { value: "motor_mount" } });
    fireEvent.change(editable[1], { target: { value: "Motor Mount" } });
    fireEvent.change(editable[2], {
      target: { value: "Printed bracket for the motor" },
    });
    clickSave();
    await flushMicrotasks();

    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "motor_mount",
        label: "Motor Mount",
        description: "Printed bracket for the motor",
      }),
    );
  });

  it("empty description is sent as null (not empty string)", async () => {
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /New Type/i }));
    const editable = editableTextInputs(container);
    fireEvent.change(editable[0], { target: { value: "empty_desc" } });
    fireEvent.change(editable[1], { target: { value: "Empty Desc" } });
    // description left blank

    clickSave();
    await flushMicrotasks();

    const payload = mockCreate.mock.calls[0][0];
    expect(payload.description).toBeNull();
  });

  it("schema is always a plain JS array (not a JSON-encoded string)", async () => {
    // Regression for the double-encoding bug:
    // backend rejected payloads where `schema` was a stringified JSON array.
    // The frontend must always send a real array — including when empty.
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /New Type/i }));
    const editable = editableTextInputs(container);
    fireEvent.change(editable[0], { target: { value: "arr_check" } });
    fireEvent.change(editable[1], { target: { value: "Arr Check" } });
    clickSave();
    await flushMicrotasks();

    const payload = mockCreate.mock.calls[0][0];
    expect(Array.isArray(payload.schema)).toBe(true);
    expect(payload.schema).toEqual([]);
  });

  it("exactly one createComponentType call per Save click (no duplicate fires)", async () => {
    // Regression for the 2026-04-16 delete-cascade incident: a UI double-fire
    // would duplicate mutations and is one plausible explanation for the
    // "delete 1 wiped the table" symptom. Even if our investigation found the
    // backend to be safe, we pin this guarantee down in the UI as well.
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /New Type/i }));
    const editable = editableTextInputs(container);
    fireEvent.change(editable[0], { target: { value: "nodup" } });
    fireEvent.change(editable[1], { target: { value: "NoDup" } });
    clickSave();
    // The Save handler is async → the dialog disables the button after
    // the first click so a second click should be a no-op.
    clickSave();
    await flushMicrotasks();

    expect(mockCreate).toHaveBeenCalledTimes(1);
  });
});

// ----------------------------------------------------------------------- //
// Property-addition sub-flow — adds a Property through the nested
// PropertyEditDialog and verifies that it appears in the final payload.
// ----------------------------------------------------------------------- //

describe("Adding properties inside the type", () => {
  it("adds a 'number' property via PropertyEditDialog → appears in Save payload", async () => {
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /New Type/i }));

    // Fill Name + Label
    let editable = editableTextInputs(container);
    fireEvent.change(editable[0], { target: { value: "tube" } });
    fireEvent.change(editable[1], { target: { value: "Tube" } });

    // Open PropertyEditDialog: Button labelled "+ Property" (inside Edit dialog)
    // There are multiple Plus icons on screen — target by text of the label.
    fireEvent.click(screen.getByText(/^Property$/));

    // PropertyEditDialog is now mounted. Fill Name + Label + Unit + Min/Max.
    // We re-query because new inputs appeared inside the nested dialog.
    editable = editableTextInputs(container);
    // Order of editable inputs now:
    //   0: outer Name
    //   1: outer Label
    //   2: outer Description
    //   3: prop Name
    //   4: prop Label
    //   5: prop Unit
    //   6: prop Description
    fireEvent.change(editable[3], { target: { value: "diameter_mm" } });
    fireEvent.change(editable[4], { target: { value: "Diameter" } });
    fireEvent.change(editable[5], { target: { value: "mm" } });

    // Number-type Min/Max/Default inputs are rendered as type="number"
    const numberInputs = container.querySelectorAll(
      'input[type="number"]',
    ) as NodeListOf<HTMLInputElement>;
    // Min, Max, Default
    expect(numberInputs.length).toBe(3);
    fireEvent.change(numberInputs[0], { target: { value: "1" } });
    fireEvent.change(numberInputs[1], { target: { value: "500" } });
    fireEvent.change(numberInputs[2], { target: { value: "25" } });

    // Apply
    fireEvent.click(screen.getByText(/^Apply$/));

    // Property row should now show in the outer dialog
    expect(screen.getByText(/diameter_mm/)).toBeDefined();
    expect(screen.getByText(/Properties \(1\)/)).toBeDefined();

    // Save the type
    clickSave();
    await flushMicrotasks();

    expect(mockCreate).toHaveBeenCalledTimes(1);
    const payload = mockCreate.mock.calls[0][0];
    expect(payload.schema).toHaveLength(1);
    expect(payload.schema[0]).toEqual(
      expect.objectContaining({
        name: "diameter_mm",
        label: "Diameter",
        type: "number",
        unit: "mm",
        min: 1,
        max: 500,
        default: 25,
      }),
    );
  });

  it("adds two properties; deletes the first; Save payload has only the survivor", async () => {
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /New Type/i }));

    const firstEditable = editableTextInputs(container);
    fireEvent.change(firstEditable[0], { target: { value: "multi" } });
    fireEvent.change(firstEditable[1], { target: { value: "Multi" } });

    // Add property #1 ("alpha")
    fireEvent.click(screen.getByText(/^Property$/));
    let editable = editableTextInputs(container);
    fireEvent.change(editable[3], { target: { value: "alpha" } });
    fireEvent.change(editable[4], { target: { value: "Alpha" } });
    fireEvent.click(screen.getByText(/^Apply$/));

    // Add property #2 ("beta")
    fireEvent.click(screen.getByText(/^Property$/));
    editable = editableTextInputs(container);
    fireEvent.change(editable[3], { target: { value: "beta" } });
    fireEvent.change(editable[4], { target: { value: "Beta" } });
    fireEvent.click(screen.getByText(/^Apply$/));

    expect(screen.getByText(/Properties \(2\)/)).toBeDefined();

    // Delete property "alpha" by finding its row and clicking its Trash icon.
    const alphaRow = screen.getByText("alpha").closest("div");
    expect(alphaRow).not.toBeNull();
    const deleteBtn = within(alphaRow as HTMLElement).getByTitle(
      /Delete property/i,
    );
    fireEvent.click(deleteBtn);

    expect(screen.getByText(/Properties \(1\)/)).toBeDefined();
    expect(screen.queryByText("alpha")).toBeNull();

    // Save
    clickSave();
    await flushMicrotasks();

    const payload = mockCreate.mock.calls[0][0];
    expect(payload.schema).toHaveLength(1);
    expect(payload.schema[0].name).toBe("beta");
  });

  it("PropertyEditDialog validation blocks Apply: enum with no options", () => {
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /New Type/i }));
    const first = editableTextInputs(container);
    fireEvent.change(first[0], { target: { value: "enum_t" } });
    fireEvent.change(first[1], { target: { value: "Enum T" } });

    fireEvent.click(screen.getByText(/^Property$/));
    const editable = editableTextInputs(container);
    fireEvent.change(editable[3], { target: { value: "color" } });
    fireEvent.change(editable[4], { target: { value: "Color" } });

    // Switch type to enum
    const select = container.querySelector("select") as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "enum" } });

    // Click Apply with empty options CSV
    fireEvent.click(screen.getByText(/^Apply$/));

    // Property-row list must still show 0 properties, inline error shown
    expect(screen.getByText(/Enum needs at least one option/i)).toBeDefined();
    expect(screen.getByText(/Properties \(0\)/)).toBeDefined();
  });
});

// ----------------------------------------------------------------------- //
// Backend error propagation — the user must see the error and the form
// must NOT reset; no duplicate mutation was fired.
// ----------------------------------------------------------------------- //

describe("Backend error propagation on Save", () => {
  it("409 conflict: error is shown, dialog stays open, form preserved", async () => {
    mockCreate.mockRejectedValueOnce(
      new Error("Type with name 'dup' already exists."),
    );
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /New Type/i }));

    const editable = editableTextInputs(container);
    fireEvent.change(editable[0], { target: { value: "dup" } });
    fireEvent.change(editable[1], { target: { value: "Dup" } });

    clickSave();

    // Error is surfaced (waitFor — the rejected promise settles on a later tick)
    await waitFor(() => {
      expect(screen.getByText(/already exists/i)).toBeDefined();
    });

    // Dialog still open — its title is still visible
    expect(screen.getByText(/New Type:/i)).toBeDefined();

    // Form values preserved
    const stillEditable = editableTextInputs(container);
    expect(stillEditable[0].value).toBe("dup");
    expect(stillEditable[1].value).toBe("Dup");

    // Parent's onSaved/mutate not fired on error
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it("422 validation: message passes through unchanged", async () => {
    mockCreate.mockRejectedValueOnce(
      new Error("Ungültige Eingabedaten"),
    );
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /New Type/i }));
    const editable = editableTextInputs(container);
    fireEvent.change(editable[0], { target: { value: "t_x" } });
    fireEvent.change(editable[1], { target: { value: "T X" } });

    clickSave();

    await waitFor(() => {
      expect(screen.getByText(/Ungültige Eingabedaten/)).toBeDefined();
    });
  });

  it("after a failed save, the user can retry: second call made on second Save", async () => {
    mockCreate
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce({ id: 5, name: "retry_me" });
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /New Type/i }));
    const editable = editableTextInputs(container);
    fireEvent.change(editable[0], { target: { value: "retry_me" } });
    fireEvent.change(editable[1], { target: { value: "Retry" } });

    clickSave();
    await waitFor(() => {
      expect(screen.getByText(/boom/)).toBeDefined();
    });
    expect(mockCreate).toHaveBeenCalledTimes(1);

    // Click Save again — this time it succeeds
    clickSave();
    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledTimes(2);
    });

    expect(mockMutate).toHaveBeenCalled();
  });
});

// ----------------------------------------------------------------------- //
// Edit + Delete surfaces — the "not-new" branch of the Edit dialog.
// ----------------------------------------------------------------------- //

describe("Edit existing type (not new)", () => {
  const existingType = {
    id: 42,
    name: "carbon_tube",
    label: "Carbon Tube",
    description: "Rolled CF tube",
    schema: [
      { name: "diameter_mm", label: "Dia", type: "number", required: true },
    ],
    deletable: true,
    reference_count: 0,
    created_at: "2026-04-16T00:00:00Z",
    updated_at: "2026-04-16T00:00:00Z",
  };

  beforeEach(() => {
    hookReturn = {
      types: [existingType],
      isLoading: false,
      mutate: mockMutate,
      error: null,
    };
  });

  it("opens with pre-filled values; Name is disabled (immutable)", () => {
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByTitle(/Edit Carbon Tube/i));

    // Name input should be disabled
    const nameInput = container.querySelector(
      'input[value="carbon_tube"]',
    ) as HTMLInputElement;
    expect(nameInput).not.toBeNull();
    expect(nameInput.disabled).toBe(true);

    // Label / Description prefilled
    expect(
      (container.querySelector('input[value="Carbon Tube"]') as HTMLInputElement)
        .disabled,
    ).toBe(false);

    // Existing property is shown
    expect(screen.getByText(/diameter_mm/)).toBeDefined();
    expect(screen.getByText(/Properties \(1\)/)).toBeDefined();
  });

  it("Save on an existing type calls updateComponentType(id, payload) — not create", async () => {
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByTitle(/Edit Carbon Tube/i));

    // Update the label and description
    const labelInput = container.querySelector(
      'input[value="Carbon Tube"]',
    ) as HTMLInputElement;
    fireEvent.change(labelInput, { target: { value: "Carbon Tube v2" } });

    clickSave();
    await flushMicrotasks();

    expect(mockCreate).not.toHaveBeenCalled();
    expect(mockUpdate).toHaveBeenCalledTimes(1);
    expect(mockUpdate).toHaveBeenCalledWith(
      42,
      expect.objectContaining({ label: "Carbon Tube v2", name: "carbon_tube" }),
    );
    expect(mockMutate).toHaveBeenCalled();
  });

  it("delete button inside edit dialog opens confirm → Confirm calls deleteComponentType(id)", async () => {
    render(<ComponentTypeManagementDialog open={true} onClose={vi.fn()} />);
    fireEvent.click(screen.getByTitle(/Edit Carbon Tube/i));

    // Delete-type button is visible because deletable=true AND ref_count=0
    fireEvent.click(screen.getByTitle(/Delete type/i));

    // Confirmation shows a Confirm button
    fireEvent.click(screen.getByText(/^Confirm$/));
    await flushMicrotasks();

    expect(mockDelete).toHaveBeenCalledTimes(1);
    expect(mockDelete).toHaveBeenCalledWith(42);
  });

  it("seeded type: delete-type button is not rendered in the edit dialog", () => {
    hookReturn = {
      types: [{ ...existingType, id: 1, name: "material", label: "Material", deletable: false }],
      isLoading: false,
      mutate: mockMutate,
      error: null,
    };
    render(<ComponentTypeManagementDialog open={true} onClose={vi.fn()} />);
    fireEvent.click(screen.getByTitle(/Edit Material/i));

    expect(screen.queryByTitle(/Delete type/i)).toBeNull();
  });

  it("referenced type: delete-type button is not rendered in the edit dialog", () => {
    hookReturn = {
      types: [{ ...existingType, reference_count: 5 }],
      isLoading: false,
      mutate: mockMutate,
      error: null,
    };
    render(<ComponentTypeManagementDialog open={true} onClose={vi.fn()} />);
    fireEvent.click(screen.getByTitle(/Edit Carbon Tube/i));

    expect(screen.queryByTitle(/Delete type/i)).toBeNull();
  });
});

// ----------------------------------------------------------------------- //
// Dialog lifecycle — Cancel does not mutate and unmounts the dialog.
// ----------------------------------------------------------------------- //

describe("Cancel / dismiss paths", () => {
  it("Cancel button in Edit dialog closes it without calling any CRUD", () => {
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /New Type/i }));

    // Type something so we can verify Cancel really drops it
    const editable = editableTextInputs(container);
    fireEvent.change(editable[0], { target: { value: "throwaway" } });
    fireEvent.change(editable[1], { target: { value: "Throwaway" } });

    // Edit dialog has a "Cancel" button (so does the outer, for the mgmt
    // dialog itself). Target the Cancel that is a sibling of the Save inside
    // the same card.
    const saveBtn = screen.getByText(/^Save$/);
    const card = saveBtn.closest("div")?.parentElement as HTMLElement;
    const cancelInsideEdit = within(card).getByText(/^Cancel$/);
    fireEvent.click(cancelInsideEdit);

    expect(mockCreate).not.toHaveBeenCalled();
    expect(mockUpdate).not.toHaveBeenCalled();
    expect(mockMutate).not.toHaveBeenCalled();

    // Edit dialog is closed (not open)
    const editDialogs = container.querySelectorAll("dialog");
    // The edit dialog is the second one (first is management dialog)
    const editDialog = editDialogs[1];
    expect(editDialog?.hasAttribute("open")).toBe(false);
  });
});
