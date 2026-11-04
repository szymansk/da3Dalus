/**
 * The property form of a fuselage section with a contour (gh-1349): the
 * contour is shown read-only, editing a/b/n warns that the contour wins, and
 * a save sends the contour back unchanged.
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
    selectedFuselageXsecIndex: 0,
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

const mockUpdateFuselageXSec = vi.fn().mockResolvedValue(undefined);
const mockMutateFuselage = vi.fn().mockResolvedValue(undefined);

const CONTOUR: [number, number][] = [
  [0, -0.04], [0.02, -0.038], [0.03, -0.02], [0.031, 0], [0.028, 0.02],
  [0.02, 0.034], [0.01, 0.04], [0, 0.041],
];
// a stable object, as SWR hands out: the form re-reads its fields only when the data change
let mockFuselage: { x_secs: Record<string, unknown>[] } = { x_secs: [] };

vi.mock("@/hooks/useFuselage", () => ({
  useFuselage: () => ({
    fuselage: mockFuselage,
    updateXSec: mockUpdateFuselageXSec,
    mutate: mockMutateFuselage,
    isLoading: false,
  }),
}));

import { PropertyForm, type PropertyFormHandle } from "@/components/workbench/PropertyForm";

function Harness() {
  const ref = useRef<PropertyFormHandle>(null);
  return (
    <>
      <PropertyForm ref={ref} onGeometryChanged={() => {}} />
      <button
        data-testid="trigger-save"
        onClick={() => {
          ref.current?.save().catch(() => {});
        }}
      >
        trigger
      </button>
    </>
  );
}

const WARNING = /contour wins for display and CAD/;

beforeEach(() => {
  vi.clearAllMocks();
  mockIsDirty = false;
  mockFuselage = {
    x_secs: [{ xyz: [0.4, 0, 0], a: 0.031, b: 0.0405, n: 2.4, contour: CONTOUR }],
  };
});

describe("FuselageXSecForm with a contour (gh-1349)", () => {
  it("shows the contour read-only and no warning before editing", () => {
    render(<Harness />);
    expect(screen.getByText(/contour \(8 points\)/)).toBeInTheDocument();
    expect(screen.queryByText(WARNING)).toBeNull();
  });

  it("warns that the contour wins once a, b or n is edited", () => {
    render(<Harness />);
    fireEvent.change(screen.getByDisplayValue("0.031"), { target: { value: "0.035" } });
    expect(screen.getByText(WARNING)).toBeInTheDocument();
  });

  it("sends the contour back unchanged with the edited fit", async () => {
    mockIsDirty = true;
    render(<Harness />);
    fireEvent.change(screen.getByDisplayValue("2.4"), { target: { value: "3" } });
    await act(async () => {
      screen.getByTestId("trigger-save").click();
    });
    const [, payload] = mockUpdateFuselageXSec.mock.calls[0];
    expect(payload.n).toBe(3);
    expect(payload.contour).toEqual(CONTOUR);
  });

  it("shows neither the contour line nor the warning for a plain section", () => {
    mockFuselage = { x_secs: [{ xyz: [0.4, 0, 0], a: 0.031, b: 0.0405, n: 2.4 }] };
    render(<Harness />);
    fireEvent.change(screen.getByDisplayValue("0.031"), { target: { value: "0.035" } });
    expect(screen.queryByText(/contour \(/)).toBeNull();
    expect(screen.queryByText(WARNING)).toBeNull();
  });
});
