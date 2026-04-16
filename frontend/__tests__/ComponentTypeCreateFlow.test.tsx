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
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
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

vi.mock("@/hooks/useComponentTypes", () => ({
  useComponentTypes: () => ({
    types: [],
    isLoading: false,
    mutate: mockMutate,
    error: null,
  }),
  createComponentType: (...a: unknown[]) => mockCreate(...a),
  updateComponentType: (...a: unknown[]) => mockUpdate(...a),
  deleteComponentType: (...a: unknown[]) => mockDelete(...a),
}));

vi.mock("@/lib/fetcher", () => ({ API_BASE: "http://x", fetcher: vi.fn() }));

import { ComponentTypeManagementDialog } from "@/components/workbench/ComponentTypeManagementDialog";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Manage Types → New Type → Save flow (e2e)", () => {
  it("creates a new type end-to-end: open mgmt → click New Type → fill form → Save → createComponentType called", async () => {
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );

    // 1. Click "+ New Type"
    fireEvent.click(screen.getByText(/New Type/i));

    // 2. Verify Edit dialog opened
    expect(screen.getByText(/New Type:/i)).toBeDefined();

    // 3. Fill in Name + Label
    // The Edit dialog has two text inputs at top: Name, Label.
    const textInputs = container.querySelectorAll(
      'input[type="text"]',
    ) as NodeListOf<HTMLInputElement>;
    // First text input across the whole DOM is the "Name" field inside the
    // edit dialog. Name input isn't disabled for new types.
    const nameInput = Array.from(textInputs).find((i) => !i.disabled) as HTMLInputElement;
    expect(nameInput).toBeDefined();
    fireEvent.change(nameInput, { target: { value: "carbon_tube" } });

    // Fill the Label input (second non-disabled text input in the edit dialog).
    const editableTextInputs = Array.from(textInputs).filter((i) => !i.disabled);
    // [name, label, description] — index 1 is label
    fireEvent.change(editableTextInputs[1], { target: { value: "Carbon Tube" } });

    // 4. Click Save
    const saveButtons = screen.getAllByText(/^Save$/);
    expect(saveButtons.length).toBeGreaterThan(0);
    fireEvent.click(saveButtons[0]);

    // 5. The backend client must have been called with the payload
    await Promise.resolve();  // flush microtasks
    await Promise.resolve();
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
    fireEvent.click(screen.getByText(/New Type/i));
    // No input → click Save
    const saveButtons = screen.getAllByText(/^Save$/);
    fireEvent.click(saveButtons[0]);
    expect(mockCreate).not.toHaveBeenCalled();
    // Inline error appears
    expect(screen.getByText(/Label is required/i)).toBeDefined();
  });

  it("Save with non-snake_case Name is blocked for new types", () => {
    const { container } = render(
      <ComponentTypeManagementDialog open={true} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByText(/New Type/i));

    const textInputs = container.querySelectorAll(
      'input[type="text"]',
    ) as NodeListOf<HTMLInputElement>;
    const editable = Array.from(textInputs).filter((i) => !i.disabled);
    fireEvent.change(editable[0], { target: { value: "CarbonTube" } });  // PascalCase
    fireEvent.change(editable[1], { target: { value: "Carbon Tube" } });

    const saveButtons = screen.getAllByText(/^Save$/);
    fireEvent.click(saveButtons[0]);

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
    fireEvent.click(screen.getByText(/New Type/i));

    const textInputs = container.querySelectorAll(
      'input[type="text"]',
    ) as NodeListOf<HTMLInputElement>;
    const editable = Array.from(textInputs).filter((i) => !i.disabled);
    fireEvent.change(editable[0], { target: { value: "t1" } });
    fireEvent.change(editable[1], { target: { value: "T1" } });

    fireEvent.click(screen.getAllByText(/^Save$/)[0]);

    // Flush the promise chain of handleSave.
    await Promise.resolve();
    await Promise.resolve();

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
    fireEvent.click(screen.getByText(/New Type/i));

    const textInputs = container.querySelectorAll(
      'input[type="text"]',
    ) as NodeListOf<HTMLInputElement>;
    const editable = Array.from(textInputs).filter((i) => !i.disabled);
    fireEvent.change(editable[0], { target: { value: "t2" } });
    fireEvent.change(editable[1], { target: { value: "T2" } });

    fireEvent.click(screen.getAllByText(/^Save$/)[0]);
    // The parent Management dialog must NOT have closed as a side-effect of
    // the Save click (Save closes the EDIT dialog via onSaved→onClose, but
    // the Management dialog's onClose must not fire).
    expect(onClose).not.toHaveBeenCalled();
  });
});
