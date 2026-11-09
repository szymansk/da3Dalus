/**
 * The property form of a fuselage body (gh-1355): role and attached_to are
 * edited when the body itself (no section) is selected, and a save sends the
 * whole body back with them.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act, fireEvent } from "@testing-library/react";
import React, { useRef } from "react";

// ── Mocks ──────────────────────────────────────────────────────

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return { ChevronDown: icon, ChevronRight: icon, Eye: icon, Box: icon };
});

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), prefetch: vi.fn() }),
}));

vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://localhost:8000",
  fetcher: vi.fn(),
}));

vi.mock("@/components/workbench/AirfoilSelector", () => ({
  AirfoilSelector: () => React.createElement("div", null, "airfoil-selector"),
}));

vi.mock("@/components/workbench/ImportFuselageDialog", () => ({
  ImportFuselageDialog: () => null,
}));

// Track isDirty so PropertyForm's imperative handle doesn't skip
let mockIsDirty = false;
const mockSetDirty = vi.fn((v: boolean) => { mockIsDirty = v; });

vi.mock("@/components/workbench/UnsavedChangesContext", () => ({
  useUnsavedChanges: () => ({
    isDirty: mockIsDirty,
    setDirty: mockSetDirty,
    registerSave: vi.fn(),
    pendingHref: null,
    isSaving: false,
    confirmDiscard: vi.fn(),
    confirmSave: vi.fn(),
    cancelNavigation: vi.fn(),
  }),
}));

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: () => ({
    aeroplaneId: "aero-1",
    selectedWing: null,
    selectedXsecIndex: null,
    selectedFuselage: "fuse-1",
    selectedFuselageXsecIndex: null,
    treeMode: "fuselage",
    setAeroplaneId: vi.fn(),
    selectWing: vi.fn(),
    selectXsec: vi.fn(),
    selectFuselage: vi.fn(),
    selectFuselageXsec: vi.fn(),
    setTreeMode: vi.fn(),
  }),
}));

vi.mock("@/hooks/useWings", () => ({
  useWing: () => ({ wing: null, updateXSec: vi.fn(), mutate: vi.fn(), isLoading: false }),
}));

vi.mock("@/hooks/useWingConfig", () => ({
  useWingConfig: () => ({ wingConfig: null, saveWingConfig: vi.fn(), mutate: vi.fn(), isLoading: false }),
}));

const mockSaveBody = vi.fn().mockResolvedValue(undefined);
let mockFuselage: Record<string, unknown> = {};

vi.mock("@/hooks/useFuselage", () => ({
  useFuselage: () => ({
    fuselage: mockFuselage,
    updateXSec: vi.fn(),
    saveBody: mockSaveBody,
    mutate: vi.fn().mockResolvedValue(undefined),
    isLoading: false,
  }),
}));

import { PropertyForm, type PropertyFormHandle } from "@/components/workbench/PropertyForm";

const BODIES = [
  { name: "fuse-1", role: "fuselage" as const, attached_to: null },
  { name: "Rumpf", role: "fuselage" as const, attached_to: null },
  { name: "Haube", role: "canopy" as const, attached_to: "fuse-1" },
];

const onGeometryChanged = vi.fn();

function Harness() {
  const ref = useRef<PropertyFormHandle>(null);
  return (
    <>
      <PropertyForm ref={ref} onGeometryChanged={onGeometryChanged} fuselageBodies={BODIES} />
      <button data-testid="trigger-save" onClick={() => { ref.current?.save().catch(() => {}); }}>
        trigger
      </button>
    </>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockIsDirty = false;
  mockFuselage = {
    name: "fuse-1",
    role: "fuselage",
    attached_to: null,
    x_secs: [{ xyz: [0, 0, 0], a: 0.03, b: 0.04, n: 2 }, { xyz: [1, 0, 0], a: 0.03, b: 0.04, n: 2 }],
  };
});

describe("Fuselage body form (gh-1355)", () => {
  it("shows the role and the bodies this one may sit on", () => {
    render(<Harness />);
    expect((screen.getByLabelText("Role") as HTMLSelectElement).value).toBe("fuselage");
    const parent = screen.getByLabelText("Attached to") as HTMLSelectElement;
    const options = Array.from(parent.options).map((o) => o.textContent);
    // the canopy sits on this body, so it cannot carry it: no cycle is offered
    expect(options).toEqual(["(none)", "Rumpf"]);
  });

  it("saves the role and the parent", async () => {
    render(<Harness />);
    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "pod" } });
    fireEvent.change(screen.getByLabelText("Attached to"), { target: { value: "Rumpf" } });
    expect(mockSetDirty).toHaveBeenCalledWith(true);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Save" }));
    });
    expect(mockSaveBody).toHaveBeenCalledWith({ role: "pod", attached_to: "Rumpf" });
    expect(onGeometryChanged).toHaveBeenCalled();
  });

  it("saves through the form handle", async () => {
    mockIsDirty = true; // the real context re-renders the form when the body form marks it dirty
    render(<Harness />);
    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "nacelle" } });
    await act(async () => {
      screen.getByTestId("trigger-save").click();
    });
    expect(mockSaveBody).toHaveBeenCalledWith({ role: "nacelle", attached_to: null });
  });

  it("notes that a canopy needs a parent and shows the backend's refusal", async () => {
    mockSaveBody.mockRejectedValueOnce(new Error("Update failed: 422 needs attached_to"));
    render(<Harness />);
    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "canopy" } });
    expect(screen.getByText("A canopy needs the body it sits on.")).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Save" }));
    });
    expect(screen.getByText(/422 needs attached_to/)).toBeInTheDocument();
  });

  it("notes that a spinner needs the body that carries the motor (gh-1375)", () => {
    render(<Harness />);
    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "spinner" } });
    expect(
      screen.getByText("A spinner needs the body that carries the motor."),
    ).toBeInTheDocument();
    const parent = screen.getByLabelText("Attached to") as HTMLSelectElement;
    expect(Array.from(parent.options).map((o) => o.textContent)).toEqual(["(none)", "Rumpf"]);
  });

  it("resets the fields on cancel", () => {
    render(<Harness />);
    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "pod" } });
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect((screen.getByLabelText("Role") as HTMLSelectElement).value).toBe("fuselage");
  });
});
