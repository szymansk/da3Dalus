import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
      { name: "wing_index", type: "str", default: null, required: true, description: "Index of the wing", options: null },
    ],
    outputs: [{ key: "{id}", description: "Complete wing assembly", options: null }],
    suggested_id: "{wing_index}.vase_wing",
  },
  {
    class_name: "ExportToStepCreator",
    category: "export_import",
    description: "Export shape to STEP file",
    parameters: [
      { name: "file_path", type: "str", default: null, required: true, description: null, options: null },
      { name: "shape_key", type: "str", default: null, required: true, description: null, options: null },
    ],
    outputs: [],
    suggested_id: "export_step",
  },
  {
    class_name: "Fuse2ShapesCreator",
    category: "cad_operations",
    description: "Boolean union of two shapes",
    parameters: [
      { name: "shape_key_a", type: "str", default: null, required: true, description: null, options: null },
      { name: "shape_key_b", type: "str", default: null, required: true, description: null, options: null },
    ],
    outputs: [{ key: "{id}", description: "Boolean union result", options: null }],
    suggested_id: "fuse.{shape_key_a}.{shape_key_b}",
  },
];

describe("CreatorGallery", () => {
  it("renders all creators when no filter is active", () => {
    render(<CreatorGallery creators={MOCK_CREATORS} onSelect={vi.fn()} />);
    expect(screen.getByText("VaseModeWingCreator")).toBeDefined();
    expect(screen.getByText("ExportToStepCreator")).toBeDefined();
    expect(screen.getByText("Fuse2ShapesCreator")).toBeDefined();
  });

  it("filters creators by search text", async () => {
    const user = userEvent.setup();
    render(<CreatorGallery creators={MOCK_CREATORS} onSelect={vi.fn()} />);
    const input = screen.getByPlaceholderText("Search creators...");
    await user.clear(input);
    await user.type(input, "vase");
    expect(screen.getByText("VaseModeWingCreator")).toBeDefined();
    expect(screen.queryByText("ExportToStepCreator")).toBeNull();
  });

  it("filters creators by category tab", async () => {
    const user = userEvent.setup();
    render(<CreatorGallery creators={MOCK_CREATORS} onSelect={vi.fn()} />);
    const exportTab = screen.getAllByText("Export").find(
      (el) => el.tagName === "BUTTON" && !el.closest(".grid"),
    )!;
    await user.click(exportTab);
    expect(screen.getByText("ExportToStepCreator")).toBeDefined();
    expect(screen.queryByText("VaseModeWingCreator")).toBeNull();
  });

  it("calls onSelect when a creator card is clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<CreatorGallery creators={MOCK_CREATORS} onSelect={onSelect} />);
    await user.click(screen.getByText("VaseModeWingCreator"));
    expect(onSelect).toHaveBeenCalledWith(MOCK_CREATORS[0]);
  });
});
