/**
 * Unit tests for TurbulatorEditDialog (gh-936).
 * Mirrors TedEditDialog.test.tsx structure/mocks.
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
  };
});

vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://localhost:8001/v2",
}));

vi.mock("@/hooks/useDialog", () => ({
  useDialog: (open: boolean, onClose: () => void) => ({
    dialogRef: { current: null },
    handleClose: onClose,
  }),
}));

import { TurbulatorEditDialog } from "@/components/workbench/TurbulatorEditDialog";

// ── Helpers ────────────────────────────────────────────────────────

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

// ── Render tests ──────────────────────────────────────────────────

describe("TurbulatorEditDialog rendering", () => {
  it("renders form dropdown with all 3 options", () => {
    render(<TurbulatorEditDialog {...defaultProps} />);
    const select = screen.getByLabelText("Form") as HTMLSelectElement;
    expect(select).toBeTruthy();
    expect(select.options.length).toBe(3);
  });

  it("renders all expected form option values", () => {
    render(<TurbulatorEditDialog {...defaultProps} />);
    const select = screen.getByLabelText("Form") as HTMLSelectElement;
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).toContain("zigzag");
    expect(values).toContain("dots");
    expect(values).toContain("thread");
  });

  it("defaults form to 'zigzag' for new turbulator", () => {
    render(<TurbulatorEditDialog {...defaultProps} />);
    const select = screen.getByLabelText("Form") as HTMLSelectElement;
    expect(select.value).toBe("zigzag");
  });

  it("renders Height field", () => {
    render(<TurbulatorEditDialog {...defaultProps} />);
    expect(screen.getByLabelText("Height (mm)")).toBeTruthy();
  });

  it("renders Position root field", () => {
    render(<TurbulatorEditDialog {...defaultProps} />);
    expect(screen.getByLabelText("Position root (x/c)")).toBeTruthy();
  });

  it("renders Position tip field", () => {
    render(<TurbulatorEditDialog {...defaultProps} />);
    expect(screen.getByLabelText("Position tip (x/c)")).toBeTruthy();
  });

  it("renders Enabled checkbox", () => {
    render(<TurbulatorEditDialog {...defaultProps} />);
    expect(screen.getByLabelText("Enabled")).toBeTruthy();
  });

  it("renders Optimize button", () => {
    render(<TurbulatorEditDialog {...defaultProps} />);
    expect(screen.getByText("Optimize")).toBeTruthy();
  });

  it("renders scope dropdown with section/segment/whole", () => {
    render(<TurbulatorEditDialog {...defaultProps} />);
    const select = screen.getByLabelText("Scope") as HTMLSelectElement;
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).toContain("section");
    expect(values).toContain("segment");
    expect(values).toContain("whole");
  });

  it("shows 'Add' button when isNew=true", () => {
    render(<TurbulatorEditDialog {...defaultProps} isNew />);
    expect(screen.getByText("Add")).toBeTruthy();
  });

  it("shows 'Save' and 'Delete' button when isNew=false", () => {
    render(<TurbulatorEditDialog {...defaultProps} isNew={false} initialData={{ form: "zigzag", height_mm: 0.3, position_root: 0.1, enabled: true }} />);
    expect(screen.getByText("Save")).toBeTruthy();
    expect(screen.getByText("Delete")).toBeTruthy();
  });

  it("no Delete button shown when isNew=true", () => {
    render(<TurbulatorEditDialog {...defaultProps} isNew />);
    expect(screen.queryByText("Delete")).toBeNull();
  });
});

// ── Pre-fill from initialData ─────────────────────────────────────

describe("TurbulatorEditDialog pre-fill", () => {
  it("pre-fills form from initialData", () => {
    render(
      <TurbulatorEditDialog
        {...defaultProps}
        isNew={false}
        initialData={{ form: "dots", height_mm: 0.4, position_root: 0.08, position_tip: 0.12, enabled: true }}
      />,
    );
    const select = screen.getByLabelText("Form") as HTMLSelectElement;
    expect(select.value).toBe("dots");
  });

  it("pre-fills height_mm from initialData", () => {
    render(
      <TurbulatorEditDialog
        {...defaultProps}
        isNew={false}
        initialData={{ form: "zigzag", height_mm: 0.5, position_root: 0.1, enabled: true }}
      />,
    );
    const heightInput = screen.getByLabelText("Height (mm)") as HTMLInputElement;
    expect(heightInput.value).toBe("0.5");
  });

  it("pre-fills position_root from initialData", () => {
    render(
      <TurbulatorEditDialog
        {...defaultProps}
        isNew={false}
        initialData={{ form: "zigzag", height_mm: 0.3, position_root: 0.15, enabled: true }}
      />,
    );
    const rootInput = screen.getByLabelText("Position root (x/c)") as HTMLInputElement;
    expect(rootInput.value).toBe("0.15");
  });

  it("pre-fills enabled=false from initialData", () => {
    render(
      <TurbulatorEditDialog
        {...defaultProps}
        isNew={false}
        initialData={{ form: "zigzag", height_mm: 0.3, position_root: 0.1, enabled: false }}
      />,
    );
    const checkbox = screen.getByLabelText("Enabled") as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
  });

  it("allows changing form via dropdown", async () => {
    const user = userEvent.setup();
    render(<TurbulatorEditDialog {...defaultProps} />);
    const select = screen.getByLabelText("Form") as HTMLSelectElement;
    await user.selectOptions(select, "thread");
    expect(select.value).toBe("thread");
  });
});

// ── Save calls PUT ─────────────────────────────────────────────────

describe("TurbulatorEditDialog save payload", () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;
  const onSaved = vi.fn();
  const onClose = vi.fn();

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

  it("Save calls PUT /turbulator endpoint", async () => {
    const user = userEvent.setup();
    render(
      <TurbulatorEditDialog
        {...defaultProps}
        onSaved={onSaved}
        onClose={onClose}
        isNew={false}
        initialData={{ form: "dots", height_mm: 0.4, position_root: 0.08, enabled: true }}
      />,
    );

    const saveBtn = screen.getByText("Save");
    await user.click(saveBtn);

    expect(fetchSpy).toHaveBeenCalled();
    const call = fetchSpy.mock.calls.find(
      (c: Parameters<typeof fetch>) => typeof c[0] === "string" && c[0].includes("/turbulator"),
    );
    expect(call).toBeTruthy();
    expect((call![1] as RequestInit).method).toBe("PUT");
    const body = JSON.parse((call![1] as RequestInit).body as string);
    expect(body.form).toBe("dots");
    expect(body.position_root).toBeCloseTo(0.08);
  });

  it("Save calls onSaved and onClose on success", async () => {
    const user = userEvent.setup();
    render(
      <TurbulatorEditDialog
        {...defaultProps}
        onSaved={onSaved}
        onClose={onClose}
        isNew={false}
        initialData={{ form: "zigzag", height_mm: 0.3, position_root: 0.1, enabled: true }}
      />,
    );

    await user.click(screen.getByText("Save"));
    expect(onSaved).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it("shows error message when PUT fails", async () => {
    fetchSpy.mockResolvedValueOnce(new Response("Server error", { status: 500 }));
    const user = userEvent.setup();
    render(
      <TurbulatorEditDialog
        {...defaultProps}
        isNew={false}
        initialData={{ form: "zigzag", height_mm: 0.3, position_root: 0.1, enabled: true }}
      />,
    );
    await user.click(screen.getByText("Save"));
    expect(screen.getByText(/500/)).toBeTruthy();
  });
});

// ── Optimize calls POST /turbulator/optimize ──────────────────────

describe("TurbulatorEditDialog optimize", () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  const mockResult = {
    sections: [
      { y_m: 0.1, chord_m: 0.2, re_local: 200_000, cl: 0.6, xtr_opt: 0.35, cd_clean: 0.030, cd_tripped: 0.020, delta_cd: -0.010, warnings: [] },
    ],
    summary: { delta_cd0: -0.002, l_d_clean: 20.0, l_d_tripped: 21.5, delta_l_d: 1.5 },
    scope: "whole",
  };

  beforeEach(() => {
    fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(mockResult), { status: 200 }),
    );
  });

  afterEach(() => {
    fetchSpy.mockRestore();
  });

  it("Optimize button calls POST /turbulator/optimize", async () => {
    const user = userEvent.setup();
    render(<TurbulatorEditDialog {...defaultProps} />);
    await user.click(screen.getByText("Optimize"));

    expect(fetchSpy).toHaveBeenCalled();
    const call = fetchSpy.mock.calls.find(
      (c: Parameters<typeof fetch>) => typeof c[0] === "string" && c[0].includes("/turbulator/optimize"),
    );
    expect(call).toBeTruthy();
    expect((call![1] as RequestInit).method).toBe("POST");
  });

  it("shows delta L/D in result after optimize", async () => {
    const user = userEvent.setup();
    render(<TurbulatorEditDialog {...defaultProps} />);
    await user.click(screen.getByText("Optimize"));

    // Wait for optimizeResult to appear
    expect(await screen.findByText(/ΔL\/D/i)).toBeTruthy();
  });

  it("shows 'no benefit' message when delta_l_d <= 0", async () => {
    const noGainResult = {
      ...mockResult,
      summary: { ...mockResult.summary, delta_l_d: -0.5 },
    };
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify(noGainResult), { status: 200 }),
    );

    const user = userEvent.setup();
    render(<TurbulatorEditDialog {...defaultProps} />);
    await user.click(screen.getByText("Optimize"));

    expect(await screen.findByText(/no benefit/i)).toBeTruthy();
  });

  it("applies xtr_opt to position fields when delta_l_d > 0", async () => {
    const user = userEvent.setup();
    render(<TurbulatorEditDialog {...defaultProps} />);
    await user.click(screen.getByText("Optimize"));

    // Wait for result to render
    await screen.findByText(/ΔL\/D/i);

    // position_root should be updated to xtr_opt = 0.35
    const rootInput = screen.getByLabelText("Position root (x/c)") as HTMLInputElement;
    expect(Number.parseFloat(rootInput.value)).toBeCloseTo(0.35, 2);
  });

  it("shows optimize error when fetch fails", async () => {
    fetchSpy.mockResolvedValueOnce(new Response("Bad Gateway", { status: 502 }));
    const user = userEvent.setup();
    render(<TurbulatorEditDialog {...defaultProps} />);
    await user.click(screen.getByText("Optimize"));
    expect(await screen.findByText(/502/)).toBeTruthy();
  });

  it("scope is forwarded in the POST body", async () => {
    const user = userEvent.setup();
    render(<TurbulatorEditDialog {...defaultProps} />);

    const scopeSelect = screen.getByLabelText("Scope") as HTMLSelectElement;
    await user.selectOptions(scopeSelect, "segment");
    await user.click(screen.getByText("Optimize"));

    const call = fetchSpy.mock.calls.find(
      (c: Parameters<typeof fetch>) => typeof c[0] === "string" && c[0].includes("/turbulator/optimize"),
    );
    const body = JSON.parse((call![1] as RequestInit).body as string);
    expect(body.scope).toBe("segment");
  });
});
