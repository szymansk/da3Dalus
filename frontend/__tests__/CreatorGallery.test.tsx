import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    Search: icon, Plus: icon, ChevronDown: icon, ChevronRight: icon, Info: icon,
  };
});

vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://localhost:8000",
  fetcher: vi.fn(),
}));

import { CreatorGallery } from "@/components/workbench/CreatorGallery";
import type { CreatorInfo } from "@/hooks/useCreators";

const MOCK_CREATORS: CreatorInfo[] = [
  {
    class_name: "VaseModeWingCreator",
    category: "wing",
    description: "Vase-mode wing with ribs, spars, TEDs",
    parameters: [
      { name: "wing_index", type: "str", default: null, required: true, description: "Index of the wing" },
    ],
    outputs: [{ key: "{id}", description: "Complete wing assembly" }],
  },
  {
    class_name: "ExportToStepCreator",
    category: "export_import",
    description: "Export shape to STEP file",
    parameters: [
      { name: "file_path", type: "str", default: null, required: true, description: null },
      { name: "shape_key", type: "str", default: null, required: true, description: null },
    ],
    outputs: [],
  },
  {
    class_name: "Fuse2ShapesCreator",
    category: "cad_operations",
    description: "Boolean union of two shapes",
    parameters: [
      { name: "shape_key_a", type: "str", default: null, required: true, description: null },
      { name: "shape_key_b", type: "str", default: null, required: true, description: null },
    ],
    outputs: [{ key: "{id}", description: "Boolean union result" }],
  },
];

describe("CreatorGallery", () => {
  it("renders all creators when no filter is active", () => {
    render(<CreatorGallery creators={MOCK_CREATORS} onSelect={vi.fn()} />);
    expect(screen.getByText("VaseModeWingCreator")).toBeDefined();
    expect(screen.getByText("ExportToStepCreator")).toBeDefined();
    expect(screen.getByText("Fuse2ShapesCreator")).toBeDefined();
  });

  it("filters creators by search text", () => {
    render(<CreatorGallery creators={MOCK_CREATORS} onSelect={vi.fn()} />);
    const input = screen.getByPlaceholderText("Search creators...");
    fireEvent.change(input, { target: { value: "vase" } });
    expect(screen.getByText("VaseModeWingCreator")).toBeDefined();
    expect(screen.queryByText("ExportToStepCreator")).toBeNull();
  });

  it("filters creators by category tab", () => {
    render(<CreatorGallery creators={MOCK_CREATORS} onSelect={vi.fn()} />);
    const exportTab = screen.getAllByText("Export").find(
      (el) => el.tagName === "BUTTON" && !el.closest(".grid"),
    )!;
    fireEvent.click(exportTab);
    expect(screen.getByText("ExportToStepCreator")).toBeDefined();
    expect(screen.queryByText("VaseModeWingCreator")).toBeNull();
  });

  it("calls onSelect when a creator card is clicked", () => {
    const onSelect = vi.fn();
    render(<CreatorGallery creators={MOCK_CREATORS} onSelect={onSelect} />);
    fireEvent.click(screen.getByText("VaseModeWingCreator"));
    expect(onSelect).toHaveBeenCalledWith(MOCK_CREATORS[0]);
  });
});
