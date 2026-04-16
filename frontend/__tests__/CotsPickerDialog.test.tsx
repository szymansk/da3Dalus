/**
 * Tests for the picker dialog that selects an existing COTS component from
 * the Component Library and reports the chosen ID back (gh#57-40g).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    X: icon, Search: icon, Loader2: icon, Package: icon,
    Plus: icon, Check: icon,
  };
});

let componentsReturnValue: {
  components: Array<Record<string, unknown>>;
  total: number;
  isLoading: boolean;
} = { components: [], total: 0, isLoading: false };

vi.mock("@/hooks/useComponents", () => ({
  useComponents: () => ({
    ...componentsReturnValue,
    error: null,
    mutate: vi.fn(),
  }),
  useComponentTypes: () => ["generic", "servo", "battery", "material"],
}));

vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://localhost:8000",
  fetcher: vi.fn(),
}));

import { CotsPickerDialog } from "@/components/workbench/CotsPickerDialog";

beforeEach(() => {
  vi.clearAllMocks();
  componentsReturnValue = { components: [], total: 0, isLoading: false };
});

describe("CotsPickerDialog", () => {
  it("does not render when open=false", () => {
    render(
      <CotsPickerDialog
        open={false}
        onClose={vi.fn()}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.queryByText(/Assign Component/i)).toBeNull();
  });

  it("renders the header with target group name when provided", () => {
    render(
      <CotsPickerDialog
        open={true}
        onClose={vi.fn()}
        onSelect={vi.fn()}
        targetGroupName="main_wing"
      />,
    );
    expect(screen.getByText(/main_wing/)).toBeDefined();
  });

  it("shows empty-state text when no components exist", () => {
    render(
      <CotsPickerDialog
        open={true}
        onClose={vi.fn()}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText(/No components/i)).toBeDefined();
  });

  it("renders a row per component returned by useComponents", () => {
    componentsReturnValue = {
      components: [
        { id: 1, name: "KST X08", component_type: "servo", manufacturer: "KST", mass_g: 7, specs: {} },
        { id: 2, name: "Sunnysky A2212", component_type: "brushless_motor", manufacturer: "Sunnysky", mass_g: 55, specs: {} },
      ],
      total: 2,
      isLoading: false,
    };

    render(
      <CotsPickerDialog
        open={true}
        onClose={vi.fn()}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByText("KST X08")).toBeDefined();
    expect(screen.getByText("Sunnysky A2212")).toBeDefined();
  });

  it("calls onSelect with the component ID and closes on pick", () => {
    componentsReturnValue = {
      components: [
        { id: 42, name: "KST X08", component_type: "servo", manufacturer: "KST", mass_g: 7, specs: {} },
      ],
      total: 1,
      isLoading: false,
    };

    const onSelect = vi.fn();
    const onClose = vi.fn();
    render(
      <CotsPickerDialog
        open={true}
        onClose={onClose}
        onSelect={onSelect}
      />,
    );

    fireEvent.click(screen.getByText("KST X08"));
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: 42, name: "KST X08" }),
    );
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes on Cancel click", () => {
    const onClose = vi.fn();
    render(
      <CotsPickerDialog
        open={true}
        onClose={onClose}
        onSelect={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByText("Cancel"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows a loading state while the library is loading", () => {
    componentsReturnValue = { components: [], total: 0, isLoading: true };

    render(
      <CotsPickerDialog
        open={true}
        onClose={vi.fn()}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText(/Loading/i)).toBeDefined();
  });
});
