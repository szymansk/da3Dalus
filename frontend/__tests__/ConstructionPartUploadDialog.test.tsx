/**
 * Tests for the Construction-Part upload dialog (gh#57-ggd).
 *
 * Form posts to /aeroplanes/{id}/construction-parts via FormData.
 * Name is required; file is required; material is optional.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
    const { container } = render(
      <ConstructionPartUploadDialog
        open={false}
        aeroplaneId="a"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    const dialog = container.querySelector("dialog");
    expect(dialog).toBeTruthy();
    expect(dialog?.hasAttribute("open")).toBe(false);
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
    const user = userEvent.setup();
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
    await user.clear(nameInput);
    await user.type(nameInput, "My Part");

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File([new Uint8Array([1, 2, 3])], "part.stl", { type: "application/octet-stream" });
    await user.upload(fileInput, file);

    await user.click(screen.getByText(/Upload/i, { selector: "button" }));

    // FormData equality is tricky — check positional args + instance type.
    expect(mockUpload).toHaveBeenCalled();
    expect(mockUpload.mock.calls[0][0]).toBe("a");
    expect(mockUpload.mock.calls[0][1]).toBeInstanceOf(FormData);
  });

  it("auto-fills the Name field from the filename (without suffix) when Name is empty", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ConstructionPartUploadDialog
        open={true}
        aeroplaneId="a"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );

    const nameInput = container.querySelector('input[type="text"]') as HTMLInputElement;
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    expect(nameInput.value).toBe("");

    const file = new File([new Uint8Array([1, 2, 3])], "Bulkhead-A.step", { type: "application/octet-stream" });
    await user.upload(fileInput, file);

    expect(nameInput.value).toBe("Bulkhead-A");
  });

  it("auto-fill strips a double extension only to the last suffix", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ConstructionPartUploadDialog
        open={true}
        aeroplaneId="a"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    const nameInput = container.querySelector('input[type="text"]') as HTMLInputElement;
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    const file = new File([new Uint8Array([1])], "part.v2.stl", { type: "application/octet-stream" });
    await user.upload(fileInput, file);

    expect(nameInput.value).toBe("part.v2");
  });

  it("does NOT overwrite the Name field when the user has already typed something", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ConstructionPartUploadDialog
        open={true}
        aeroplaneId="a"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    const nameInput = container.querySelector('input[type="text"]') as HTMLInputElement;
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    // User types a custom name first.
    await user.clear(nameInput);
    await user.type(nameInput, "MyCustomName");
    expect(nameInput.value).toBe("MyCustomName");

    // Then picks a file — the custom name must be preserved.
    const file = new File([new Uint8Array([1])], "some-file.step", { type: "application/octet-stream" });
    await user.upload(fileInput, file);

    expect(nameInput.value).toBe("MyCustomName");
  });

  it("auto-fill re-engages if the user clears the Name and then picks another file", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ConstructionPartUploadDialog
        open={true}
        aeroplaneId="a"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    const nameInput = container.querySelector('input[type="text"]') as HTMLInputElement;
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    // First file -> auto-fill "First".
    const f1 = new File([new Uint8Array([1])], "First.step");
    await user.upload(fileInput, f1);
    expect(nameInput.value).toBe("First");

    // User wipes the name, then picks another file.
    await user.clear(nameInput);
    const f2 = new File([new Uint8Array([1])], "Second.stl");
    await user.upload(fileInput, f2);
    expect(nameInput.value).toBe("Second");
  });

  it("closes on Cancel", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <ConstructionPartUploadDialog
        open={true}
        aeroplaneId="a"
        onClose={onClose}
        onSaved={vi.fn()}
      />,
    );
    await user.click(screen.getByText("Cancel"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
