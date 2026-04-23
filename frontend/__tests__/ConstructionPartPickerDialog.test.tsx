/**
 * Tests for the Construction-Parts picker (gh#57-wvg).
 *
 * Parallel to CotsPickerDialog but sourced from
 * /aeroplanes/{id}/construction-parts (the D1 endpoint, merged in PR #68).
 * Selecting a part returns the part object; the caller creates a
 * `cad_shape` tree node with `construction_part_id` set (N1 wiring).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    X: icon, Search: icon, Loader2: icon, Box: icon, Lock: icon,
  };
});

let partsReturnValue: {
  parts: Array<Record<string, unknown>>;
  total: number;
  isLoading: boolean;
} = { parts: [], total: 0, isLoading: false };

vi.mock("@/hooks/useConstructionParts", () => ({
  useConstructionParts: () => ({
    ...partsReturnValue,
    error: null,
    mutate: vi.fn(),
  }),
}));

vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://x",
  fetcher: vi.fn(),
}));

import { ConstructionPartPickerDialog } from "@/components/workbench/ConstructionPartPickerDialog";

beforeEach(() => {
  vi.clearAllMocks();
  partsReturnValue = { parts: [], total: 0, isLoading: false };
});

describe("ConstructionPartPickerDialog", () => {
  it("does not render when open=false", () => {
    const { container } = render(
      <ConstructionPartPickerDialog
        open={false}
        aeroplaneId="a"
        onClose={vi.fn()}
        onSelect={vi.fn()}
      />,
    );
    const dialog = container.querySelector("dialog");
    expect(dialog).toBeTruthy();
    expect(dialog?.hasAttribute("open")).toBe(false);
  });

  it("renders with target group name in the header", () => {
    render(
      <ConstructionPartPickerDialog
        open={true}
        aeroplaneId="a"
        onClose={vi.fn()}
        onSelect={vi.fn()}
        targetGroupName="main_wing"
      />,
    );
    expect(screen.getByText(/main_wing/)).toBeDefined();
  });

  it("shows empty-state when no parts exist", () => {
    render(
      <ConstructionPartPickerDialog
        open={true}
        aeroplaneId="a"
        onClose={vi.fn()}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText(/No construction parts/i)).toBeDefined();
  });

  it("shows loading state", () => {
    partsReturnValue = { parts: [], total: 0, isLoading: true };
    render(
      <ConstructionPartPickerDialog
        open={true}
        aeroplaneId="a"
        onClose={vi.fn()}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText(/Loading/i)).toBeDefined();
  });

  it("renders a row per part with name and volume", () => {
    partsReturnValue = {
      parts: [
        { id: 1, name: "Bulkhead-A", volume_mm3: 12500, area_mm2: 800, locked: false, material_component_id: null, file_format: "step" },
        { id: 2, name: "Frame-B", volume_mm3: 25000, area_mm2: 1200, locked: true, material_component_id: null, file_format: "stl" },
      ],
      total: 2,
      isLoading: false,
    };
    render(
      <ConstructionPartPickerDialog
        open={true}
        aeroplaneId="a"
        onClose={vi.fn()}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText("Bulkhead-A")).toBeDefined();
    expect(screen.getByText("Frame-B")).toBeDefined();
  });

  it("calls onSelect with the part on row click and closes", () => {
    partsReturnValue = {
      parts: [
        { id: 42, name: "MyPart", volume_mm3: 500, area_mm2: 50, locked: false, material_component_id: null, file_format: "stl" },
      ],
      total: 1,
      isLoading: false,
    };
    const onSelect = vi.fn();
    const onClose = vi.fn();
    render(
      <ConstructionPartPickerDialog
        open={true}
        aeroplaneId="a"
        onClose={onClose}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByText("MyPart"));
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: 42, name: "MyPart" }),
    );
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes on Cancel", () => {
    const onClose = vi.fn();
    render(
      <ConstructionPartPickerDialog
        open={true}
        aeroplaneId="a"
        onClose={onClose}
        onSelect={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText("Cancel"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("filters by search", () => {
    partsReturnValue = {
      parts: [
        { id: 1, name: "Bulkhead", volume_mm3: 100, area_mm2: 10, locked: false, material_component_id: null, file_format: "step" },
        { id: 2, name: "Frame", volume_mm3: 200, area_mm2: 20, locked: false, material_component_id: null, file_format: "step" },
      ],
      total: 2,
      isLoading: false,
    };
    render(
      <ConstructionPartPickerDialog
        open={true}
        aeroplaneId="a"
        onClose={vi.fn()}
        onSelect={vi.fn()}
      />,
    );
    const input = screen.getByPlaceholderText(/search/i) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "bulk" } });
    expect(screen.getByText("Bulkhead")).toBeDefined();
    expect(screen.queryByText("Frame")).toBeNull();
  });
});
