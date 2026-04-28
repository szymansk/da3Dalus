/**
 * Integration tests for FuselageXSecForm's imperative save handle,
 * tested via PropertyForm in fuselage mode (GH#359).
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

vi.mock("@/hooks/useFuselage", () => ({
  useFuselage: () => ({
    fuselage: {
      x_secs: [{ xyz: [1.0, 2.0, 3.0], a: 0.05, b: 0.04, n: 2.5 }],
    },
    updateXSec: mockUpdateFuselageXSec,
    mutate: mockMutateFuselage,
    isLoading: false,
  }),
}));

import { PropertyForm, type PropertyFormHandle } from "@/components/workbench/PropertyForm";

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
});

describe("FuselageXSecForm imperative save (via PropertyForm fuselage mode)", () => {
  it("renders fuselage xsec form fields", () => {
    render(<Harness />);
    expect(screen.getByDisplayValue("1")).toBeInTheDocument();
  });

  it("calls updateFuselageXSec with built payload on imperative save", async () => {
    mockIsDirty = true;
    render(<Harness />);

    await act(async () => {
      screen.getByTestId("trigger-save").click();
    });

    expect(mockUpdateFuselageXSec).toHaveBeenCalledOnce();
    const [index, payload] = mockUpdateFuselageXSec.mock.calls[0];
    expect(index).toBe(0);
    expect(payload.xyz).toEqual([1.0, 2.0, 3.0]);
    expect(payload.a).toBe(0.05);
    expect(payload.b).toBe(0.04);
    expect(payload.n).toBe(2.5);
  });

  it("skips save when not dirty", async () => {
    mockIsDirty = false;
    render(<Harness />);

    await act(async () => {
      screen.getByTestId("trigger-save").click();
    });

    expect(mockUpdateFuselageXSec).not.toHaveBeenCalled();
  });

  it("propagates save failure as thrown error", async () => {
    mockIsDirty = true;
    mockUpdateFuselageXSec.mockRejectedValueOnce(new Error("network error"));

    let caughtError: unknown = null;
    render(<Harness onSaveResult={(err) => { caughtError = err; }} />);

    await act(async () => {
      screen.getByTestId("trigger-save").click();
    });

    expect(caughtError).toBeInstanceOf(Error);
  });
});
