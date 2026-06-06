/**
 * GH-869: Eye-button (airfoil preview) in the X-Sec (ASB) wing editor.
 *
 * Verifies:
 *  1. The eye-button renders next to the airfoil field in ASB/x-sec mode.
 *  2. Clicking it calls `selectXsec` with the current index (so the preview
 *     page opens on the right airfoil) and then navigates to
 *     /workbench/airfoil-preview.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

// ── Icon stubs ─────────────────────────────────────────────────
vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", { ...props, "data-testid": `icon-${String(props.className ?? "icon")}` });
  return {
    ChevronDown: icon,
    ChevronRight: icon,
    Eye: (props: Record<string, unknown>) =>
      React.createElement("span", { ...props, "data-testid": "eye-icon" }),
    Box: icon,
  };
});

// ── next/navigation ────────────────────────────────────────────
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, prefetch: vi.fn() }),
}));

// ── misc stubs ─────────────────────────────────────────────────
vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://localhost:8000",
  fetcher: vi.fn(),
}));

vi.mock("@/components/workbench/AirfoilSelector", () => ({
  AirfoilSelector: ({ label }: { label: string }) =>
    React.createElement("div", { "data-testid": `airfoil-selector-${label}` }, label),
}));

vi.mock("@/components/workbench/ImportFuselageDialog", () => ({
  ImportFuselageDialog: () => null,
}));

vi.mock("@/components/workbench/UnsavedChangesContext", () => ({
  useUnsavedChanges: () => ({
    isDirty: false,
    setDirty: vi.fn(),
    registerSave: vi.fn(),
    pendingHref: null,
    isSaving: false,
    confirmDiscard: vi.fn(),
    confirmSave: vi.fn(),
    cancelNavigation: vi.fn(),
  }),
}));

// ── Controllable context ───────────────────────────────────────
const mockSelectXsec = vi.fn();
let ctxOverrides: Record<string, unknown> = {};

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: () => ({
    aeroplaneId: "aero-1",
    selectedWing: "wing-1",
    selectedXsecIndex: 2,          // non-zero index to test selectXsec call
    selectedFuselage: null,
    selectedFuselageXsecIndex: null,
    treeMode: "asb",
    setAeroplaneId: vi.fn(),
    selectWing: vi.fn(),
    selectXsec: mockSelectXsec,
    selectFuselage: vi.fn(),
    selectFuselageXsec: vi.fn(),
    setTreeMode: vi.fn(),
    ...ctxOverrides,
  }),
}));

// ── Wing data ─────────────────────────────────────────────────
const mockXsec = {
  airfoil: "mh32",
  chord: 0.3,
  twist: 2,
  xyz_le: [0, 0, 0] as [number, number, number],
  x_sec_type: "uniform",
};

vi.mock("@/hooks/useWings", () => ({
  useWing: () => ({
    wing: { x_secs: [mockXsec, mockXsec, mockXsec], design_model: "asb" },
    updateXSec: vi.fn().mockResolvedValue(undefined),
    mutate: vi.fn().mockResolvedValue(undefined),
    isLoading: false,
  }),
}));

vi.mock("@/hooks/useWingConfig", () => ({
  useWingConfig: () => ({
    wingConfig: null,
    saveWingConfig: vi.fn(),
    mutate: vi.fn(),
    isLoading: false,
  }),
}));

vi.mock("@/hooks/useFuselage", () => ({
  useFuselage: () => ({
    fuselage: null,
    updateXSec: vi.fn(),
    mutate: vi.fn(),
    isLoading: false,
  }),
}));

import { PropertyForm } from "@/components/workbench/PropertyForm";

// ── Tests ──────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  ctxOverrides = {};
});

describe("GH-869: eye-button in ASB/x-sec mode", () => {
  it("renders an eye-button next to the airfoil selector in ASB mode", () => {
    render(<PropertyForm />);
    // The airfoil selector must be present
    expect(screen.getByTestId("airfoil-selector-airfoil")).toBeTruthy();
    // The eye-button must be present (identified by title attribute)
    const eyeBtn = screen.getByTitle("Preview airfoil");
    expect(eyeBtn).toBeTruthy();
    // Eye icon inside
    expect(screen.getByTestId("eye-icon")).toBeTruthy();
  });

  it("clicking the eye-button calls selectXsec with the current index and navigates to /workbench/airfoil-preview", () => {
    render(<PropertyForm />);
    const eyeBtn = screen.getByTitle("Preview airfoil");
    fireEvent.click(eyeBtn);
    // selectXsec must be called with the current xsec index (2)
    expect(mockSelectXsec).toHaveBeenCalledWith(2);
    // router.push must navigate to the preview page
    expect(mockPush).toHaveBeenCalledWith("/workbench/airfoil-preview");
  });
});
