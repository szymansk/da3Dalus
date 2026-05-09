/**
 * Unit tests for the TedEditDialog (gh-439, gh-450).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// ── Mocks ─────────────────────────────────────────────────────────

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    X: icon,
    Check: icon,
    ChevronDown: icon,
    ChevronUp: icon,
    Search: icon,
    ChevronRight: icon,
  };
});

vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://localhost:8001/v2",
}));

vi.mock("@/hooks/useComponents", () => ({
  useComponents: () => ({ components: [] }),
}));

vi.mock("@/hooks/useDialog", () => ({
  useDialog: (open: boolean, onClose: () => void) => ({
    dialogRef: { current: null },
    handleClose: onClose,
  }),
}));

import { TedEditDialog } from "@/components/workbench/TedEditDialog";

// ── Tests ─────────────────────────────────────────────────────────

describe("TedEditDialog role dropdown", () => {
  const defaultProps = {
    open: true,
    onClose: vi.fn(),
    aeroplaneId: "1",
    wingName: "Main Wing",
    xsecIndex: 0,
    isNew: true,
    initialData: undefined,
    onSaved: vi.fn(),
  };

  it("renders role dropdown with all 8 options", () => {
    render(<TedEditDialog {...defaultProps} />);
    const select = screen.getByLabelText("Role") as HTMLSelectElement;
    expect(select).toBeTruthy();
    expect(select.options.length).toBe(8);
  });

  it("defaults role to 'other' for new TED", () => {
    render(<TedEditDialog {...defaultProps} />);
    const select = screen.getByLabelText("Role") as HTMLSelectElement;
    expect(select.value).toBe("other");
  });

  it("renders optional label input", () => {
    render(<TedEditDialog {...defaultProps} />);
    expect(screen.getByPlaceholderText("e.g. Left Aileron")).toBeTruthy();
  });

  it("pre-fills role from initialData", () => {
    render(
      <TedEditDialog
        {...defaultProps}
        isNew={false}
        initialData={{ role: "elevator", label: "Main Elevator" }}
      />
    );
    const select = screen.getByLabelText("Role") as HTMLSelectElement;
    expect(select.value).toBe("elevator");
  });

  it("pre-fills label from initialData", () => {
    render(
      <TedEditDialog
        {...defaultProps}
        isNew={false}
        initialData={{ role: "aileron", label: "Left Aileron" }}
      />
    );
    const labelInput = screen.getByPlaceholderText("e.g. Left Aileron") as HTMLInputElement;
    expect(labelInput.value).toBe("Left Aileron");
  });

  it("allows changing role via dropdown", async () => {
    const user = userEvent.setup();
    render(<TedEditDialog {...defaultProps} />);
    const select = screen.getByLabelText("Role") as HTMLSelectElement;
    await user.selectOptions(select, "elevator");
    expect(select.value).toBe("elevator");
  });

  it("renders all expected role option values", () => {
    render(<TedEditDialog {...defaultProps} />);
    const select = screen.getByLabelText("Role") as HTMLSelectElement;
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).toContain("elevator");
    expect(values).toContain("aileron");
    expect(values).toContain("rudder");
    expect(values).toContain("elevon");
    expect(values).toContain("stabilator");
    expect(values).toContain("flap");
    expect(values).toContain("spoiler");
    expect(values).toContain("other");
  });
});

describe("TedEditDialog save payload (gh-450)", () => {
  const onSaved = vi.fn();
  const onClose = vi.fn();
  const defaultProps = {
    open: true,
    onClose,
    aeroplaneId: "1",
    wingName: "Main Wing",
    xsecIndex: 0,
    isNew: false,
    initialData: { role: "elevator", label: "Main Elevator", rel_chord_root: 0.8 },
    onSaved,
  };

  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({}), { status: 200 }),
    );
    onSaved.mockClear();
    onClose.mockClear();
  });

  afterEach(() => {
    fetchSpy.mockRestore();
  });

  it("sends role and label in TED PATCH payload", async () => {
    const user = userEvent.setup();
    render(<TedEditDialog {...defaultProps} />);

    const saveBtn = screen.getByText("Save");
    await user.click(saveBtn);

    expect(fetchSpy).toHaveBeenCalled();
    const tedCall = fetchSpy.mock.calls.find(
      (c) => typeof c[0] === "string" && c[0].includes("/trailing_edge_device"),
    );
    expect(tedCall).toBeTruthy();
    const body = JSON.parse((tedCall![1] as RequestInit).body as string);
    expect(body.role).toBe("elevator");
    expect(body.label).toBe("Main Elevator");
  });

  it("sends null label when label is cleared", async () => {
    const user = userEvent.setup();
    render(<TedEditDialog {...defaultProps} />);

    const labelInput = screen.getByPlaceholderText("e.g. Left Aileron") as HTMLInputElement;
    await user.clear(labelInput);

    const saveBtn = screen.getByText("Save");
    await user.click(saveBtn);

    const tedCall = fetchSpy.mock.calls.find(
      (c) => typeof c[0] === "string" && c[0].includes("/trailing_edge_device"),
    );
    const body = JSON.parse((tedCall![1] as RequestInit).body as string);
    expect(body.label).toBeNull();
  });

  it("sends changed role after dropdown selection", async () => {
    const user = userEvent.setup();
    render(<TedEditDialog {...defaultProps} />);

    const select = screen.getByLabelText("Role") as HTMLSelectElement;
    await user.selectOptions(select, "aileron");

    const saveBtn = screen.getByText("Save");
    await user.click(saveBtn);

    const tedCall = fetchSpy.mock.calls.find(
      (c) => typeof c[0] === "string" && c[0].includes("/trailing_edge_device"),
    );
    const body = JSON.parse((tedCall![1] as RequestInit).body as string);
    expect(body.role).toBe("aileron");
  });
});
