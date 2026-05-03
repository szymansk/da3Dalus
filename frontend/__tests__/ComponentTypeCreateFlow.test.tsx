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
import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
async function clickSave(user: ReturnType<typeof userEvent.setup>) {
  const saveButtons = screen.getAllByText(/^Save$/);
  expect(saveButtons.length).toBeGreaterThan(0);
  await user.click(saveButtons[0]);
}

describe("Manage Types → New Type → Save flow (e2e)", () => {
  it("creates a new type end-to-end: open mgmt → click New Type → fill form → Save → createComponentType called", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );

    // 1. Click "+ New Type"
    await user.click(screen.getByRole("button", { name: /New Type/i }));

    // 2. Verify Edit dialog opened
    expect(screen.getByText(/New Type:/i)).toBeDefined();

    // 3. Fill in Name + Label
    const editable = editableTextInputs(container);
    await user.clear(editable[0]);
    await user.type(editable[0], "carbon_tube");
    // [name, label, description] — index 1 is label
    await user.clear(editable[1]);
    await user.type(editable[1], "Carbon Tube");

    // 4. Click Save
    await clickSave(user);

    // 5. The backend client must have been called with the payload
    expect(mockCreate).toHaveBeenCalledTimes(1);
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "carbon_tube",
        label: "Carbon Tube",
        schema: [],
      }),
    );
  });

  it("Save with empty Label is blocked — no API call", async () => {
    const user = userEvent.setup();
    render(<ComponentTypeManagementDialog open={true} onClose={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: /New Type/i }));
    // No input → click Save
    await clickSave(user);
    expect(mockCreate).not.toHaveBeenCalled();
    // Inline error appears
    expect(screen.getByText(/Label is required/i)).toBeDefined();
  });

  it("Save with non-snake_case Name is blocked for new types", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    await user.click(screen.getByRole("button", { name: /New Type/i }));

    const editable = editableTextInputs(container);
    await user.clear(editable[0]);
    await user.type(editable[0], "CarbonTube");  // PascalCase
    await user.clear(editable[1]);
    await user.type(editable[1], "Carbon Tube");

    await clickSave(user);

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
    const user = userEvent.setup();
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    await user.click(screen.getByRole("button", { name: /New Type/i }));

    const editable = editableTextInputs(container);
    await user.clear(editable[0]);
    await user.type(editable[0], "t1");
    await user.clear(editable[1]);
    await user.type(editable[1], "T1");

    await clickSave(user);

    expect(mockMutate).toHaveBeenCalled();
  });

  it("clicking Save propagates: no event handler outside the dialog triggers before handleSave", async () => {
    // Guards against a regression where stopPropagation on the inner card
    // is dropped — which would let the parent backdrop's onClick close the
    // dialog before the async save settles.
    const user = userEvent.setup();
    const onClose = vi.fn();
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={onClose} />,
    );
    await user.click(screen.getByRole("button", { name: /New Type/i }));

    const editable = editableTextInputs(container);
    await user.clear(editable[0]);
    await user.type(editable[0], "t2");
    await user.clear(editable[1]);
    await user.type(editable[1], "T2");

    await clickSave(user);
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
    const user = userEvent.setup();
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    await user.click(screen.getByRole("button", { name: /New Type/i }));
    const editable = editableTextInputs(container);
    await user.clear(editable[0]);
    await user.type(editable[0], "motor_mount");
    await user.clear(editable[1]);
    await user.type(editable[1], "Motor Mount");
    await user.clear(editable[2]);
    await user.type(editable[2], "Printed bracket for the motor");
    await clickSave(user);

    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "motor_mount",
        label: "Motor Mount",
        description: "Printed bracket for the motor",
      }),
    );
  });

  it("empty description is sent as null (not empty string)", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    await user.click(screen.getByRole("button", { name: /New Type/i }));
    const editable = editableTextInputs(container);
    await user.clear(editable[0]);
    await user.type(editable[0], "empty_desc");
    await user.clear(editable[1]);
    await user.type(editable[1], "Empty Desc");
    // description left blank

    await clickSave(user);

    const payload = mockCreate.mock.calls[0][0];
    expect(payload.description).toBeNull();
  });

  it("schema is always a plain JS array (not a JSON-encoded string)", async () => {
    // Regression for the double-encoding bug:
    // backend rejected payloads where `schema` was a stringified JSON array.
    // The frontend must always send a real array — including when empty.
    const user = userEvent.setup();
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    await user.click(screen.getByRole("button", { name: /New Type/i }));
    const editable = editableTextInputs(container);
    await user.clear(editable[0]);
    await user.type(editable[0], "arr_check");
    await user.clear(editable[1]);
    await user.type(editable[1], "Arr Check");
    await clickSave(user);

    const payload = mockCreate.mock.calls[0][0];
    expect(Array.isArray(payload.schema)).toBe(true);
    expect(payload.schema).toEqual([]);
  });

  it("exactly one createComponentType call per Save click (no duplicate fires)", async () => {
    // Regression for the 2026-04-16 delete-cascade incident: a UI double-fire
    // would duplicate mutations and is one plausible explanation for the
    // "delete 1 wiped the table" symptom. Even if our investigation found the
    // backend to be safe, we pin this guarantee down in the UI as well.
    //
    // Use a deferred promise so the Save handler stays pending while we
    // attempt a second click. The button should be disabled after the first
    // click (React re-renders between awaited userEvent calls).
    let resolveCreate!: (v: unknown) => void;
    mockCreate.mockImplementationOnce(
      () => new Promise((r) => { resolveCreate = r; }),
    );

    const user = userEvent.setup();
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    await user.click(screen.getByRole("button", { name: /New Type/i }));
    const editable = editableTextInputs(container);
    await user.clear(editable[0]);
    await user.type(editable[0], "nodup");
    await user.clear(editable[1]);
    await user.type(editable[1], "NoDup");

    // First click — starts the save, button becomes disabled while pending
    await user.click(screen.getAllByText(/^Save$/)[0]);

    // Second click — button is disabled, so this should be a no-op
    await user.click(screen.getAllByText(/^Save$/)[0]);

    // Resolve the pending save
    resolveCreate({ id: 999, name: "nodup" });
    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledTimes(1);
    });
  });
});

// ----------------------------------------------------------------------- //
// Property-addition sub-flow — adds a Property through the nested
// PropertyEditDialog and verifies that it appears in the final payload.
// ----------------------------------------------------------------------- //

describe("Adding properties inside the type", () => {
  it("adds a 'number' property via PropertyEditDialog → appears in Save payload", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    await user.click(screen.getByRole("button", { name: /New Type/i }));

    // Fill Name + Label
    let editable = editableTextInputs(container);
    await user.clear(editable[0]);
    await user.type(editable[0], "tube");
    await user.clear(editable[1]);
    await user.type(editable[1], "Tube");

    // Open PropertyEditDialog: Button labelled "+ Property" (inside Edit dialog)
    // There are multiple Plus icons on screen — target by text of the label.
    await user.click(screen.getByText(/^Property$/));

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
    await user.clear(editable[3]);
    await user.type(editable[3], "diameter_mm");
    await user.clear(editable[4]);
    await user.type(editable[4], "Diameter");
    await user.clear(editable[5]);
    await user.type(editable[5], "mm");

    // Number-type Min/Max/Default inputs are rendered as type="number"
    const numberInputs = container.querySelectorAll(
      'input[type="number"]',
    ) as NodeListOf<HTMLInputElement>;
    // Min, Max, Default
    expect(numberInputs.length).toBe(3);
    await user.clear(numberInputs[0]);
    await user.type(numberInputs[0], "1");
    await user.clear(numberInputs[1]);
    await user.type(numberInputs[1], "500");
    await user.clear(numberInputs[2]);
    await user.type(numberInputs[2], "25");

    // Apply
    await user.click(screen.getByText(/^Apply$/));

    // Property row should now show in the outer dialog
    expect(screen.getByText(/diameter_mm/)).toBeDefined();
    expect(screen.getByText(/Properties \(1\)/)).toBeDefined();

    // Save the type
    await clickSave(user);

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
    const user = userEvent.setup();
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    await user.click(screen.getByRole("button", { name: /New Type/i }));

    const firstEditable = editableTextInputs(container);
    await user.clear(firstEditable[0]);
    await user.type(firstEditable[0], "multi");
    await user.clear(firstEditable[1]);
    await user.type(firstEditable[1], "Multi");

    // Add property #1 ("alpha")
    await user.click(screen.getByText(/^Property$/));
    let editable = editableTextInputs(container);
    await user.clear(editable[3]);
    await user.type(editable[3], "alpha");
    await user.clear(editable[4]);
    await user.type(editable[4], "Alpha");
    await user.click(screen.getByText(/^Apply$/));

    // Add property #2 ("beta")
    await user.click(screen.getByText(/^Property$/));
    editable = editableTextInputs(container);
    await user.clear(editable[3]);
    await user.type(editable[3], "beta");
    await user.clear(editable[4]);
    await user.type(editable[4], "Beta");
    await user.click(screen.getByText(/^Apply$/));

    expect(screen.getByText(/Properties \(2\)/)).toBeDefined();

    // Delete property "alpha" by finding its row and clicking its Trash icon.
    const alphaRow = screen.getByText("alpha").closest("div");
    expect(alphaRow).not.toBeNull();
    const deleteBtn = within(alphaRow as HTMLElement).getByTitle(
      /Delete property/i,
    );
    await user.click(deleteBtn);

    expect(screen.getByText(/Properties \(1\)/)).toBeDefined();
    expect(screen.queryByText("alpha")).toBeNull();

    // Save
    await clickSave(user);

    const payload = mockCreate.mock.calls[0][0];
    expect(payload.schema).toHaveLength(1);
    expect(payload.schema[0].name).toBe("beta");
  });

  it("PropertyEditDialog validation blocks Apply: enum with no options", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    await user.click(screen.getByRole("button", { name: /New Type/i }));
    const first = editableTextInputs(container);
    await user.clear(first[0]);
    await user.type(first[0], "enum_t");
    await user.clear(first[1]);
    await user.type(first[1], "Enum T");

    await user.click(screen.getByText(/^Property$/));
    const editable = editableTextInputs(container);
    await user.clear(editable[3]);
    await user.type(editable[3], "color");
    await user.clear(editable[4]);
    await user.type(editable[4], "Color");

    // Switch type to enum
    const select = container.querySelector("select") as HTMLSelectElement;
    await user.selectOptions(select, "enum");

    // Click Apply with empty options CSV
    await user.click(screen.getByText(/^Apply$/));

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
    const user = userEvent.setup();
    mockCreate.mockRejectedValueOnce(
      new Error("Type with name 'dup' already exists."),
    );
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    await user.click(screen.getByRole("button", { name: /New Type/i }));

    const editable = editableTextInputs(container);
    await user.clear(editable[0]);
    await user.type(editable[0], "dup");
    await user.clear(editable[1]);
    await user.type(editable[1], "Dup");

    await clickSave(user);

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
    const user = userEvent.setup();
    mockCreate.mockRejectedValueOnce(
      new Error("Ungültige Eingabedaten"),
    );
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    await user.click(screen.getByRole("button", { name: /New Type/i }));
    const editable = editableTextInputs(container);
    await user.clear(editable[0]);
    await user.type(editable[0], "t_x");
    await user.clear(editable[1]);
    await user.type(editable[1], "T X");

    await clickSave(user);

    await waitFor(() => {
      expect(screen.getByText(/Ungültige Eingabedaten/)).toBeDefined();
    });
  });

  it("after a failed save, the user can retry: second call made on second Save", async () => {
    const user = userEvent.setup();
    mockCreate
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce({ id: 5, name: "retry_me" });
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    await user.click(screen.getByRole("button", { name: /New Type/i }));
    const editable = editableTextInputs(container);
    await user.clear(editable[0]);
    await user.type(editable[0], "retry_me");
    await user.clear(editable[1]);
    await user.type(editable[1], "Retry");

    await clickSave(user);
    await waitFor(() => {
      expect(screen.getByText(/boom/)).toBeDefined();
    });
    expect(mockCreate).toHaveBeenCalledTimes(1);

    // Click Save again — this time it succeeds
    await clickSave(user);
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

  it("opens with pre-filled values; Name is disabled (immutable)", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    await user.click(screen.getByTitle(/Edit Carbon Tube/i));

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
    const user = userEvent.setup();
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    await user.click(screen.getByTitle(/Edit Carbon Tube/i));

    // Update the label and description
    const labelInput = container.querySelector(
      'input[value="Carbon Tube"]',
    ) as HTMLInputElement;
    await user.clear(labelInput);
    await user.type(labelInput, "Carbon Tube v2");

    await clickSave(user);

    expect(mockCreate).not.toHaveBeenCalled();
    expect(mockUpdate).toHaveBeenCalledTimes(1);
    expect(mockUpdate).toHaveBeenCalledWith(
      42,
      expect.objectContaining({ label: "Carbon Tube v2", name: "carbon_tube" }),
    );
    expect(mockMutate).toHaveBeenCalled();
  });

  it("delete button inside edit dialog opens confirm → Confirm calls deleteComponentType(id)", async () => {
    const user = userEvent.setup();
    render(<ComponentTypeManagementDialog open={true} onClose={vi.fn()} />);
    await user.click(screen.getByTitle(/Edit Carbon Tube/i));

    // Delete-type button is visible because deletable=true AND ref_count=0
    await user.click(screen.getByTitle(/Delete type/i));

    // Confirmation shows a Confirm button
    await user.click(screen.getByText(/^Confirm$/));

    expect(mockDelete).toHaveBeenCalledTimes(1);
    expect(mockDelete).toHaveBeenCalledWith(42);
  });

  it("seeded type: delete-type button is not rendered in the edit dialog", async () => {
    const user = userEvent.setup();
    hookReturn = {
      types: [{ ...existingType, id: 1, name: "material", label: "Material", deletable: false }],
      isLoading: false,
      mutate: mockMutate,
      error: null,
    };
    render(<ComponentTypeManagementDialog open={true} onClose={vi.fn()} />);
    await user.click(screen.getByTitle(/Edit Material/i));

    expect(screen.queryByTitle(/Delete type/i)).toBeNull();
  });

  it("referenced type: delete-type button is not rendered in the edit dialog", async () => {
    const user = userEvent.setup();
    hookReturn = {
      types: [{ ...existingType, reference_count: 5 }],
      isLoading: false,
      mutate: mockMutate,
      error: null,
    };
    render(<ComponentTypeManagementDialog open={true} onClose={vi.fn()} />);
    await user.click(screen.getByTitle(/Edit Carbon Tube/i));

    expect(screen.queryByTitle(/Delete type/i)).toBeNull();
  });
});

// ----------------------------------------------------------------------- //
// Dialog lifecycle — Cancel does not mutate and unmounts the dialog.
// ----------------------------------------------------------------------- //

describe("Cancel / dismiss paths", () => {
  it("Cancel button in Edit dialog closes it without calling any CRUD", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    await user.click(screen.getByRole("button", { name: /New Type/i }));

    // Type something so we can verify Cancel really drops it
    const editable = editableTextInputs(container);
    await user.clear(editable[0]);
    await user.type(editable[0], "throwaway");
    await user.clear(editable[1]);
    await user.type(editable[1], "Throwaway");

    // Edit dialog has a "Cancel" button (so does the outer, for the mgmt
    // dialog itself). Target the Cancel that is a sibling of the Save inside
    // the same card.
    const saveBtn = screen.getByText(/^Save$/);
    const card = saveBtn.closest("div")?.parentElement as HTMLElement;
    const cancelInsideEdit = within(card).getByText(/^Cancel$/);
    await user.click(cancelInsideEdit);

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
