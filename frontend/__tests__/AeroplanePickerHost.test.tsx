/**
 * Unit tests for AeroplanePickerHost (gh-695).
 *
 * The host wires the AeroplanePickerDialog props from the
 * AeroplaneContext + useAeroplanes hook and adds the `onImport`
 * callback that persists warnings into context, selects the imported
 * aeroplane, and refreshes SWR caches.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

const setAeroplaneId = vi.fn();
const closePicker = vi.fn();
const setLastImportWarnings = vi.fn();
const createAeroplane = vi.fn();
const deleteAeroplane = vi.fn();
const mutate = vi.fn();
const globalMutate = vi.fn();

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: () => ({
    aeroplaneId: "aero-current",
    setAeroplaneId,
    pickerOpen: true,
    closePicker,
    setLastImportWarnings,
  }),
}));

vi.mock("@/hooks/useAeroplanes", () => ({
  useAeroplanes: () => ({
    aeroplanes: [
      { id: "aero-current", name: "Current", total_mass_kg: null, created_at: "", updated_at: "" },
    ],
    createAeroplane,
    deleteAeroplane,
    mutate,
  }),
}));

vi.mock("swr", () => ({
  useSWRConfig: () => ({ mutate: globalMutate }),
}));

// Stub the dialog with a minimal harness that exposes the callbacks
// via buttons we can fire from the test.
vi.mock("@/components/workbench/construction-plans/AeroplanePickerDialog", () => ({
  AeroplanePickerDialog: ({
    onSelect,
    onDelete,
    onCreate,
    onImport,
  }: {
    onSelect: (id: string) => Promise<void>;
    onDelete: (id: string) => Promise<void>;
    onCreate: (name: string) => Promise<void>;
    onImport: (response: {
      aeroplane_uuid: string;
      warnings: Array<{ component_type: string; component_name: string; reason: string; severity: "info" | "warning" | "error" }>;
    }) => void;
  }) => (
    <div>
      <button onClick={() => onSelect("aero-x")}>select</button>
      <button onClick={() => onDelete("aero-current")}>delete-current</button>
      <button onClick={() => onCreate("new-name")}>create</button>
      <button
        onClick={() =>
          onImport({
            aeroplane_uuid: "aero-imported",
            warnings: [
              {
                component_type: "PROP",
                component_name: "MainProp",
                reason: "phase 2",
                severity: "warning",
              },
            ],
          })
        }
      >
        import
      </button>
    </div>
  ),
}));

import { AeroplanePickerHost } from "@/components/workbench/AeroplanePickerHost";

describe("AeroplanePickerHost", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("on select: sets aeroplaneId and closes the picker", async () => {
    render(<AeroplanePickerHost />);
    fireEvent.click(screen.getByText("select"));
    // Microtask flush
    await Promise.resolve();
    expect(setAeroplaneId).toHaveBeenCalledWith("aero-x");
    expect(closePicker).toHaveBeenCalled();
  });

  it("on delete of current aeroplane: clears aeroplaneId", async () => {
    deleteAeroplane.mockResolvedValueOnce(undefined);
    render(<AeroplanePickerHost />);
    fireEvent.click(screen.getByText("delete-current"));
    // delete is async — flush a microtask cycle
    await Promise.resolve();
    await Promise.resolve();
    expect(deleteAeroplane).toHaveBeenCalledWith("aero-current");
    expect(setAeroplaneId).toHaveBeenCalledWith(null);
  });

  it("on create: sets aeroplaneId from server response + closes picker", async () => {
    createAeroplane.mockResolvedValueOnce({ id: "aero-new", name: "new-name" });
    render(<AeroplanePickerHost />);
    fireEvent.click(screen.getByText("create"));
    await Promise.resolve();
    await Promise.resolve();
    expect(createAeroplane).toHaveBeenCalledWith("new-name");
    expect(setAeroplaneId).toHaveBeenCalledWith("aero-new");
    expect(closePicker).toHaveBeenCalled();
  });

  it("on import: captures warnings, selects imported aeroplane, refreshes SWR, closes picker", () => {
    render(<AeroplanePickerHost />);
    fireEvent.click(screen.getByText("import"));
    expect(setLastImportWarnings).toHaveBeenCalledWith({
      uuid: "aero-imported",
      warnings: [
        {
          component_type: "PROP",
          component_name: "MainProp",
          reason: "phase 2",
          severity: "warning",
        },
      ],
    });
    expect(setAeroplaneId).toHaveBeenCalledWith("aero-imported");
    expect(mutate).toHaveBeenCalled();
    expect(globalMutate).toHaveBeenCalled();
    expect(closePicker).toHaveBeenCalled();
  });

  it("globalMutate filter matches keys containing the imported uuid", () => {
    render(<AeroplanePickerHost />);
    fireEvent.click(screen.getByText("import"));
    const [predicate] = globalMutate.mock.calls.at(-1) as [
      (k: unknown) => boolean,
    ];
    expect(predicate("/api/v2/aeroplanes/aero-imported/wings")).toBe(true);
    expect(predicate("/api/v2/aeroplanes/other-uuid/wings")).toBe(false);
    expect(predicate(123)).toBe(false);
  });
});
