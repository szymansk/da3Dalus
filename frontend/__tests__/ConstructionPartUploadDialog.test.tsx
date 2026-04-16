/**
 * Tests for the Construction-Part upload dialog (gh#57-ggd).
 *
 * Form posts to /aeroplanes/{id}/construction-parts via FormData.
 * Name is required; file is required; material is optional.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return { X: icon, Loader2: icon, Upload: icon };
});

const mockUpload = vi.fn().mockResolvedValue({ id: 1, name: "New Part" });

vi.mock("@/hooks/useConstructionParts", () => ({
  uploadConstructionPart: (...a: unknown[]) => mockUpload(...a),
  useConstructionParts: () => ({ parts: [], total: 0, isLoading: false, error: null, mutate: vi.fn() }),
  lockConstructionPart: vi.fn(),
  unlockConstructionPart: vi.fn(),
  deleteConstructionPart: vi.fn(),
  updateConstructionPart: vi.fn(),
}));

vi.mock("@/hooks/useComponents", () => ({
  useComponents: () => ({
    components: [
      { id: 42, name: "PLA+", component_type: "material", manufacturer: "eSUN", specs: { density_kg_m3: 1240 } },
    ],
    total: 1, isLoading: false, error: null, mutate: vi.fn(),
  }),
  useComponentTypes: () => ["material"],
}));

vi.mock("@/lib/fetcher", () => ({ API_BASE: "http://x", fetcher: vi.fn() }));

import { ConstructionPartUploadDialog } from "@/components/workbench/ConstructionPartUploadDialog";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ConstructionPartUploadDialog", () => {
  it("does not render when open=false", () => {
    render(
      <ConstructionPartUploadDialog
        open={false}
        aeroplaneId="a"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    expect(screen.queryByText(/Upload Construction Part/i)).toBeNull();
  });

  it("renders name input, file input, and material dropdown", () => {
    render(
      <ConstructionPartUploadDialog
        open={true}
        aeroplaneId="a"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    expect(screen.getByText(/Name/)).toBeDefined();
    expect(screen.getByText(/File/)).toBeDefined();
    expect(screen.getByText(/Material/)).toBeDefined();
    // The material dropdown should list available materials
    expect(screen.getByText(/PLA\+/)).toBeDefined();
  });

  it("upload button is disabled until name and file are both provided", () => {
    render(
      <ConstructionPartUploadDialog
        open={true}
        aeroplaneId="a"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    const submit = screen.getByText(/Upload/i, { selector: "button" }) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
  });

  it("posts FormData with name + file on submit", async () => {
    const onSaved = vi.fn();
    const onClose = vi.fn();
    const { container } = render(
      <ConstructionPartUploadDialog
        open={true}
        aeroplaneId="a"
        onClose={onClose}
        onSaved={onSaved}
      />,
    );

    const nameInput = container.querySelector('input[type="text"]') as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: "My Part" } });

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File([new Uint8Array([1, 2, 3])], "part.stl", { type: "application/octet-stream" });
    Object.defineProperty(fileInput, "files", { value: [file] });
    fireEvent.change(fileInput);

    fireEvent.click(screen.getByText(/Upload/i, { selector: "button" }));

    // FormData equality is tricky — check positional args + instance type.
    expect(mockUpload).toHaveBeenCalled();
    expect(mockUpload.mock.calls[0][0]).toBe("a");
    expect(mockUpload.mock.calls[0][1]).toBeInstanceOf(FormData);
  });

  it("closes on Cancel", () => {
    const onClose = vi.fn();
    render(
      <ConstructionPartUploadDialog
        open={true}
        aeroplaneId="a"
        onClose={onClose}
        onSaved={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText("Cancel"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
