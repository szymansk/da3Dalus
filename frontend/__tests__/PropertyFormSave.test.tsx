/**
 * Integration tests for PropertyForm's imperative save handle
 * and FuselageXSecForm's imperative save handle.
 *
 * These test the actual components (not mocks) to cover the
 * useImperativeHandle save dispatch logic added in GH#359.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import React, { useRef } from "react";

// ── Mocks ──────────────────────────────────────────────────────

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    ChevronDown: icon, ChevronRight: icon, Eye: icon, Box: icon,
  };
});

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), prefetch: vi.fn() }),
}));

vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://localhost:8000",
  fetcher: vi.fn(),
}));

// AirfoilSelector — stub to avoid complex dependency chain
vi.mock("@/components/workbench/AirfoilSelector", () => ({
  AirfoilSelector: () => React.createElement("div", null, "airfoil-selector"),
}));

// ImportFuselageDialog — stub
vi.mock("@/components/workbench/ImportFuselageDialog", () => ({
  ImportFuselageDialog: () => null,
}));

// ── Controllable mock values ───────────────────────────────────

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

const mockUpdateXSec = vi.fn().mockResolvedValue(undefined);
const mockMutateWing = vi.fn().mockResolvedValue(undefined);
const mockSaveWingConfig = vi.fn().mockResolvedValue(undefined);
const mockMutateWc = vi.fn().mockResolvedValue(undefined);
const mockUpdateFuselageXSec = vi.fn().mockResolvedValue(undefined);
const mockMutateFuselage = vi.fn().mockResolvedValue(undefined);

const mockXsec = {
  airfoil: "mh32",
  chord: 0.3,
  twist: 2,
  xyz_le: [0, 0, 0] as [number, number, number],
};

const mockSegment = {
  root_airfoil: { airfoil: "mh32", chord: 300, dihedral_as_rotation_in_degrees: 0, incidence: 0 },
  tip_airfoil: { airfoil: "mh32", chord: 200, dihedral_as_rotation_in_degrees: 0, incidence: 0 },
  length: 500,
  sweep: 50,
  number_interpolation_points: 201,
  tip_type: "",
};

const mockWingConfig = {
  segments: [mockSegment],
  nose_pnt: [0, 0, 0],
  symmetric: true,
};

let ctxOverrides: Record<string, unknown> = {};

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: () => ({
    aeroplaneId: "aero-1",
    selectedWing: "wing-1",
    selectedXsecIndex: 0,
    selectedFuselage: null,
    selectedFuselageXsecIndex: null,
    treeMode: "wingconfig",
    setAeroplaneId: vi.fn(),
    selectWing: vi.fn(),
    selectXsec: vi.fn(),
    selectFuselage: vi.fn(),
    selectFuselageXsec: vi.fn(),
    setTreeMode: vi.fn(),
    ...ctxOverrides,
  }),
}));

vi.mock("@/hooks/useWings", () => ({
  useWing: () => ({
    wing: { x_secs: [mockXsec], design_model: null },
    updateXSec: mockUpdateXSec,
    mutate: mockMutateWing,
    isLoading: false,
  }),
}));

vi.mock("@/hooks/useWingConfig", () => ({
  useWingConfig: () => ({
    wingConfig: mockWingConfig,
    saveWingConfig: mockSaveWingConfig,
    mutate: mockMutateWc,
    isLoading: false,
  }),
}));

vi.mock("@/hooks/useFuselage", () => ({
  useFuselage: () => ({
    fuselage: { x_secs: [{ xyz: [0, 0, 0], a: 0.05, b: 0.04, n: 2 }] },
    updateXSec: mockUpdateFuselageXSec,
    mutate: mockMutateFuselage,
    isLoading: false,
  }),
}));

import { PropertyForm, type PropertyFormHandle } from "@/components/workbench/PropertyForm";

// ── Test harness ───────────────────────────────────────────────

function Harness({ onSaveResult }: { onSaveResult?: (err: unknown) => void }) {
  const ref = useRef<PropertyFormHandle>(null);
  return (
    <>
      <PropertyForm ref={ref} onGeometryChanged={() => {}} />
      <button
        data-testid="trigger-save"
        onClick={() => {
          ref.current?.save()
            .then(() => onSaveResult?.(null))
            .catch((err) => onSaveResult?.(err));
        }}
      >
        trigger
      </button>
    </>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockIsDirty = false;
  ctxOverrides = {};
});

// ── Tests ──────────────────────────────────────────────────────

describe("PropertyForm imperative save handle", () => {
  it("skips save when not dirty", async () => {
    mockIsDirty = false;
    render(<Harness />);
    await act(async () => {
      screen.getByTestId("trigger-save").click();
    });
    expect(mockSaveWingConfig).not.toHaveBeenCalled();
    expect(mockUpdateXSec).not.toHaveBeenCalled();
  });

  it("calls saveWingConfig in wingconfig mode when dirty", async () => {
    mockIsDirty = true;
    ctxOverrides = { treeMode: "wingconfig" };
    render(<Harness />);
    await act(async () => {
      screen.getByTestId("trigger-save").click();
    });
    expect(mockSaveWingConfig).toHaveBeenCalledOnce();
  });

  it("calls updateXSec in asb mode when dirty", async () => {
    mockIsDirty = true;
    ctxOverrides = { treeMode: "asb" };
    render(<Harness />);
    await act(async () => {
      screen.getByTestId("trigger-save").click();
    });
    expect(mockUpdateXSec).toHaveBeenCalledOnce();
  });

  it("throws when wingconfig save fails", async () => {
    mockIsDirty = true;
    ctxOverrides = { treeMode: "wingconfig" };
    mockSaveWingConfig.mockRejectedValueOnce(new Error("network error"));

    let caughtError: unknown = null;
    render(<Harness onSaveResult={(err) => { caughtError = err; }} />);
    await act(async () => {
      screen.getByTestId("trigger-save").click();
    });
    expect(caughtError).toBeInstanceOf(Error);
    expect((caughtError as Error).message).toBe("Save failed");
  });

  it("throws when asb save fails", async () => {
    mockIsDirty = true;
    ctxOverrides = { treeMode: "asb" };
    mockUpdateXSec.mockRejectedValueOnce(new Error("network error"));

    let caughtError: unknown = null;
    render(<Harness onSaveResult={(err) => { caughtError = err; }} />);
    await act(async () => {
      screen.getByTestId("trigger-save").click();
    });
    expect(caughtError).toBeInstanceOf(Error);
    expect((caughtError as Error).message).toBe("Save failed");
  });
});
