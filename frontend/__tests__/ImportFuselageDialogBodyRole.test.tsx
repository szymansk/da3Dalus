/**
 * The fuselage import / 3D edit dialog sets role and attached_to of the body
 * (gh-1355) and keeps them, with the mirror flag, when it saves the sections.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import React from "react";

vi.mock("@/lib/fetcher", () => ({ API_BASE: "http://api.test" }));
vi.mock("plotly.js-gl3d-dist-min", () => ({
  default: { newPlot: vi.fn(), react: vi.fn(), purge: vi.fn(), relayout: vi.fn(), restyle: vi.fn() },
}));

import { ImportFuselageDialog, type XSec } from "@/components/workbench/ImportFuselageDialog";

const SECTIONS: XSec[] = [
  { xyz: [0.2, 0, 0.05], a: 0.03, b: 0.04, n: 2, n_lower: 1 },
  { xyz: [0.5, 0, 0.05], a: 0.03, b: 0.04, n: 2, n_lower: 1 },
];
const BODIES = [
  { name: "Rumpf", role: "fuselage" as const, attached_to: null },
  { name: "Haube", role: "canopy" as const, attached_to: "Rumpf" },
];

afterEach(() => vi.unstubAllGlobals());

function renderEdit(onSaved = vi.fn()) {
  render(
    <ImportFuselageDialog
      open
      onClose={vi.fn()}
      onSaved={onSaved}
      aeroplaneId="aero-1"
      initialXsecs={SECTIONS}
      initialName="Haube"
      initialBody={{ role: "canopy", attached_to: "Rumpf", symmetric: true }}
      bodies={BODIES}
    />,
  );
}

describe("ImportFuselageDialog body role (gh-1355)", () => {
  it("starts from the edited body's role and parent", () => {
    renderEdit();
    expect((screen.getByLabelText("Role") as HTMLSelectElement).value).toBe("canopy");
    const parent = screen.getByLabelText("Attached to") as HTMLSelectElement;
    expect(parent.value).toBe("Rumpf");
    expect(Array.from(parent.options).map((o) => o.value)).toEqual(["", "Rumpf"]);
  });

  it("saves the chosen role and parent and keeps the mirror flag", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal("fetch", fetchMock);
    const onSaved = vi.fn();
    renderEdit(onSaved);

    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "fairing" } });
    fireEvent.change(screen.getByLabelText("Attached to"), { target: { value: "" } });
    await act(async () => {
      fireEvent.click(screen.getByText("Accept & Save"));
    });

    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect([body.role, body.attached_to, body.symmetric]).toEqual(["fairing", null, true]);
    expect(onSaved).toHaveBeenCalled();
  });

  it("starts a new body as a fuselage on nothing", () => {
    render(<ImportFuselageDialog open onClose={vi.fn()} aeroplaneId="aero-1" bodies={BODIES} />);
    fireEvent.click(screen.getByText("Create manually"));
    expect((screen.getByLabelText("Role") as HTMLSelectElement).value).toBe("fuselage");
    expect((screen.getByLabelText("Attached to") as HTMLSelectElement).value).toBe("");
  });
});
