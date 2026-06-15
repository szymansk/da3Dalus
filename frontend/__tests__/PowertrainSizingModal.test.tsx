/**
 * Unit tests for PowertrainSizingModal (gh-197).
 *
 * Tests cover:
 *  - Button presence in ComponentsPage header
 *  - Modal opens on button click
 *  - Aero params (cd0, s_ref) pre-filled and displayed
 *  - Warnings banner when defaults are used
 *  - Motor picker table renders and allows selection
 *  - Motor selection updates eta_motor display
 *  - Run Sizing button calls the API
 *  - Results table renders candidates
 *  - Add to Component Tree calls addTreeNode and closes modal
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import type { PowertrainModalParamsResponse } from "@/hooks/usePowertrainSizingModal";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", { ...props, "data-testid": "icon" });
  return {
    Package: icon, Search: icon, Plus: icon, Settings: icon, Trash2: icon,
    X: icon, Loader2: icon, ChevronDown: icon, ChevronRight: icon,
    Box: icon, Lock: icon, Unlock: icon, Upload: icon,
    FolderPlus: icon, Check: icon, GripVertical: icon,
    Pencil: icon, Scale: icon, Zap: icon, AlertTriangle: icon,
    ExternalLink: icon,
  };
});

// Mutable SWR return for powertrain modal params
let modalParamsReturn: {
  data: PowertrainModalParamsResponse | null | undefined;
  error: unknown;
  isLoading: boolean;
  mutate: ReturnType<typeof vi.fn>;
} = {
  data: undefined,
  error: null,
  isLoading: false,
  mutate: vi.fn(),
};

const runPowertrainSizingMock = vi.fn();
vi.mock("@/hooks/usePowertrainSizingModal", () => ({
  usePowertrainModalParams: () => modalParamsReturn,
  runPowertrainSizing: (...args: unknown[]) => runPowertrainSizingMock(...args),
}));

vi.mock("@/hooks/useMissionObjectives", () => ({
  useMissionObjectives: () => ({
    data: { target_cruise_mps: 18.0 },
    error: null,
    isLoading: false,
  }),
}));

const addTreeNodeMock = vi.fn().mockResolvedValue({});
vi.mock("@/hooks/useComponentTree", () => ({
  useComponentTree: () => ({
    tree: [],
    totalNodes: 0,
    error: null,
    isLoading: false,
    mutate: vi.fn(),
  }),
  addTreeNode: (...args: unknown[]) => addTreeNodeMock(...args),
  deleteTreeNode: vi.fn().mockResolvedValue(undefined),
  moveTreeNode: vi.fn().mockResolvedValue({}),
}));

vi.mock("@/hooks/useComponents", () => ({
  useComponents: () => ({
    components: [],
    total: 0,
    error: null,
    isLoading: false,
    mutate: vi.fn(),
  }),
  deleteComponent: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/hooks/useConstructionParts", () => ({
  useConstructionParts: () => ({
    parts: [],
    total: 0,
    error: null,
    isLoading: false,
    mutate: vi.fn(),
  }),
  uploadConstructionPart: vi.fn().mockResolvedValue({}),
  deleteConstructionPart: vi.fn().mockResolvedValue(undefined),
  updateConstructionPart: vi.fn().mockResolvedValue({}),
  lockConstructionPart: vi.fn().mockResolvedValue({}),
  unlockConstructionPart: vi.fn().mockResolvedValue({}),
}));

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: () => ({
    aeroplaneId: "aero-1",
    selectedWing: null,
    selectedXsecIndex: null,
    selectedFuselage: null,
    selectedFuselageXsecIndex: null,
    treeMode: "wingconfig",
    setAeroplaneId: vi.fn(),
    selectWing: vi.fn(),
    selectXsec: vi.fn(),
    selectFuselage: vi.fn(),
    selectFuselageXsec: vi.fn(),
    setTreeMode: vi.fn(),
  }),
}));

vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://localhost:8001",
  fetcher: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const DEFAULTS: PowertrainModalParamsResponse = {
  altitude_m: 0.0,
  cd0: 0.025,
  s_ref_m2: 0.42,
  eta_prop: 0.65,
  eta_motor: 0.85,
  motors: [
    {
      id: 1,
      name: "D-Power M2826/10",
      manufacturer: "D-Power",
      mass_g: 55.0,
      efficiency_pct: 83.0,
      kv: 1100,
      max_power_w: 350.0,
      description: null,
    },
    {
      id: 2,
      name: "D-Power M2228/05",
      manufacturer: "D-Power",
      mass_g: 35.0,
      efficiency_pct: 80.0,
      kv: 1800,
      max_power_w: 170.0,
      description: null,
    },
  ],
  warnings: [],
};

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

async function openSizingModal(): Promise<void> {
  const user = userEvent.setup();
  const btn = screen.getByTestId("powertrain-sizing-btn");
  await user.click(btn);
}

// ---------------------------------------------------------------------------
// Tests: ComponentsPage integration
// ---------------------------------------------------------------------------

import ComponentsPage from "@/app/workbench/components/page";

describe("ComponentsPage — Powertrain Sizing button", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    modalParamsReturn = {
      data: DEFAULTS,
      error: null,
      isLoading: false,
      mutate: vi.fn(),
    };
  });

  it("renders the Powertrain Sizing button when aeroplane is selected", () => {
    render(<ComponentsPage />);
    expect(screen.getByTestId("powertrain-sizing-btn")).toBeTruthy();
  });

  it("opens the Powertrain Sizing modal on button click", async () => {
    render(<ComponentsPage />);
    await openSizingModal();

    await waitFor(() => {
      expect(screen.getByTestId("powertrain-sizing-modal")).toBeTruthy();
    });
  });
});

// ---------------------------------------------------------------------------
// Tests: PowertrainSizingModal component in isolation
// ---------------------------------------------------------------------------

import { PowertrainSizingModal } from "@/components/workbench/PowertrainSizingModal";

const onCloseMock = vi.fn();
const onTreeMutateMock = vi.fn();

function renderModal(overrides: Partial<PowertrainModalParamsResponse> = {}) {
  modalParamsReturn = {
    data: { ...DEFAULTS, ...overrides },
    error: null,
    isLoading: false,
    mutate: vi.fn(),
  };

  return render(
    <PowertrainSizingModal
      open={true}
      aeroplaneId="aero-1"
      onClose={onCloseMock}
      onTreeMutate={onTreeMutateMock}
    />
  );
}

describe("PowertrainSizingModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    runPowertrainSizingMock.mockResolvedValue({
      recommendations: [],
      warnings: [],
    });
  });

  it("renders the modal with the correct aria-label", () => {
    renderModal();
    const dialog = screen.getByRole("dialog", { name: /Powertrain Sizing/i });
    expect(dialog).toBeTruthy();
  });

  it("shows the Roxxy Fibel link", () => {
    renderModal();
    const link = screen.getByTestId("roxxy-fibel-link");
    expect(link.getAttribute("href")).toContain("multiplex-rc.de");
    expect(link.getAttribute("target")).toBe("_blank");
  });

  it("displays cd0 from defaults", () => {
    renderModal();
    const cd0Input = screen.getByTestId("input-cd0") as HTMLInputElement;
    expect(parseFloat(cd0Input.value)).toBeCloseTo(0.025, 3);
  });

  it("displays s_ref as read-only", () => {
    renderModal();
    const srefInput = screen.getByTestId("input-sref") as HTMLInputElement;
    expect(parseFloat(srefInput.value)).toBeCloseTo(0.42, 2);
    expect(srefInput.readOnly).toBe(true);
  });

  it("shows warnings banner when warnings are present", () => {
    renderModal({ warnings: ["cd0 defaulted to 0.03"] });
    expect(screen.getByTestId("modal-warnings")).toBeTruthy();
    expect(screen.getByText(/cd0 defaulted/i)).toBeTruthy();
  });

  it("renders the motor table with catalog motors", () => {
    renderModal();
    expect(screen.getByTestId("motor-table")).toBeTruthy();
    expect(screen.getByTestId("motor-row-1")).toBeTruthy();
    expect(screen.getByTestId("motor-row-2")).toBeTruthy();
  });

  it("filters motors by search", async () => {
    const user = userEvent.setup();
    renderModal();

    const searchInput = screen.getByTestId("motor-search");
    await user.type(searchInput, "M2826");

    await waitFor(() => {
      expect(screen.queryByTestId("motor-row-1")).toBeTruthy(); // M2826/10 matches
      expect(screen.queryByTestId("motor-row-2")).toBeNull();   // M2228/05 does not match
    });
  });

  it("shows notice after motor selection", async () => {
    const user = userEvent.setup();
    renderModal();

    await user.click(screen.getByTestId("motor-row-1"));

    await waitFor(() => {
      expect(screen.getByTestId("motor-selected-notice")).toBeTruthy();
    });
  });

  it("calls runPowertrainSizing when Run Sizing is clicked", async () => {
    const user = userEvent.setup();
    renderModal();

    await user.click(screen.getByTestId("run-sizing-btn"));

    await waitFor(() => {
      expect(runPowertrainSizingMock).toHaveBeenCalledWith(
        "aero-1",
        expect.objectContaining({
          cd0: 0.025,
          s_ref_m2: 0.42,
          eta_prop: 0.65,
          eta_motor: 0.85,
          altitude_m: 0.0,
        })
      );
    });
  });

  it("renders results table when candidates are returned", async () => {
    runPowertrainSizingMock.mockResolvedValue({
      recommendations: [
        {
          motor_id: 1,
          motor_name: "D-Power M2826/10",
          esc_id: 10,
          esc_name: "YGE 60A",
          battery_id: 20,
          battery_name: "Turnigy 2200",
          propeller: null,
          estimated_flight_time_min: 12.5,
          estimated_cruise_power_w: 85.0,
          estimated_top_speed_ms: 25.0,
          confidence: 0.72,
        },
      ],
      warnings: [],
    });

    const user = userEvent.setup();
    renderModal();
    await user.click(screen.getByTestId("run-sizing-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("results-section")).toBeTruthy();
      // Motor name appears in both motor table and results table — getAllByText handles both
      expect(screen.getAllByText("D-Power M2826/10").length).toBeGreaterThanOrEqual(1);
    });
  });

  it("calls addTreeNode and onTreeMutate when Add to Component Tree is clicked", async () => {
    runPowertrainSizingMock.mockResolvedValue({
      recommendations: [
        {
          motor_id: 1,
          motor_name: "D-Power M2826/10",
          esc_id: 10,
          esc_name: "YGE 60A",
          battery_id: 20,
          battery_name: "Turnigy 2200",
          propeller: null,
          estimated_flight_time_min: 12.5,
          estimated_cruise_power_w: 85.0,
          estimated_top_speed_ms: 25.0,
          confidence: 0.72,
        },
      ],
      warnings: [],
    });

    const user = userEvent.setup();
    renderModal();
    await user.click(screen.getByTestId("run-sizing-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("results-section")).toBeTruthy();
    });

    // Select the candidate row
    const candidateRow = screen.getByTestId("candidate-row-1-20");
    await user.click(candidateRow);

    // Click add to tree
    const addBtn = screen.getByTestId("add-to-tree-btn");
    await user.click(addBtn);

    await waitFor(() => {
      expect(addTreeNodeMock).toHaveBeenCalledWith(
        "aero-1",
        expect.objectContaining({ node_type: "cots", component_id: 1 })
      );
      expect(addTreeNodeMock).toHaveBeenCalledWith(
        "aero-1",
        expect.objectContaining({ node_type: "cots", component_id: 10 })
      );
      expect(onTreeMutateMock).toHaveBeenCalled();
      expect(onCloseMock).toHaveBeenCalled();
    });
  });

  it("closes when the close button is clicked", async () => {
    const user = userEvent.setup();
    renderModal();
    await user.click(screen.getByTestId("modal-close-btn"));
    expect(onCloseMock).toHaveBeenCalled();
  });
});
