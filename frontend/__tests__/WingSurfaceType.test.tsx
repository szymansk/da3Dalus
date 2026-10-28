/**
 * GH-1187: wing role (surface_type) selector, create bodies, swap, inferred marker.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";

vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://api/v2",
  fetcher: vi.fn(),
}));

vi.mock("@/hooks/useDialog", () => ({
  useDialog: () => ({ dialogRef: { current: null }, handleClose: vi.fn() }),
}));

import { CreateWingDialog } from "@/components/workbench/CreateWingDialog";
import { WingSurfaceTypePanel } from "@/components/workbench/WingSurfaceType";
import { SURFACE_TYPES, SURFACE_TYPE_LABELS } from "@/lib/surfaceType";

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockResolvedValue({ ok: true, text: async () => "", json: async () => ({}) });
  vi.stubGlobal("fetch", fetchMock);
});

function lastBody(): Record<string, unknown> {
  const call = fetchMock.mock.calls.at(-1)!;
  return JSON.parse(call[1].body as string);
}

describe("CreateWingDialog role selector", () => {
  it("lists all roles with English labels and preselects Main wing on an empty aeroplane", () => {
    render(<CreateWingDialog open onClose={vi.fn()} aeroplaneId="a1" />);
    const select = screen.getByLabelText("Wing role") as HTMLSelectElement;
    expect(select.value).toBe("main_wing");
    expect(Array.from(select.options).map((o) => o.text)).toEqual(
      SURFACE_TYPES.map((t) => SURFACE_TYPE_LABELS[t]),
    );
    expect(screen.getByText(/Exactly one per aeroplane/)).toBeTruthy();
  });

  it("defaults to Horizontal tail and disables Main wing when a main wing exists", () => {
    render(<CreateWingDialog open onClose={vi.fn()} aeroplaneId="a1" mainWingName="w" />);
    const select = screen.getByLabelText("Wing role") as HTMLSelectElement;
    expect(select.value).toBe("horizontal_tail");
    const main = Array.from(select.options).find((o) => o.value === "main_wing")!;
    expect(main.disabled).toBe(true);
    expect(screen.getByText(/Change roles on the existing wing first/)).toBeTruthy();
  });

  it("sends surface_type on the WingConfig create path", async () => {
    render(<CreateWingDialog open onClose={vi.fn()} aeroplaneId="a1" />);
    fireEvent.change(screen.getByLabelText("Wing name"), { target: { value: "tail" } });
    fireEvent.change(screen.getByLabelText("Wing role"), { target: { value: "v_tail" } });
    fireEvent.click(screen.getByRole("button", { name: "Create", hidden: true }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][0]).toContain("/from-wingconfig");
    expect(lastBody().surface_type).toBe("v_tail");
    expect(lastBody().segments).toBeDefined();
  });

  it("sends surface_type on the ASB create path", async () => {
    render(<CreateWingDialog open onClose={vi.fn()} aeroplaneId="a1" />);
    fireEvent.change(screen.getByLabelText("Wing name"), { target: { value: "w" } });
    fireEvent.click(screen.getByLabelText("Position-based (ASB)"));
    fireEvent.click(screen.getByRole("button", { name: "Create", hidden: true }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][1].method).toBe("PUT");
    expect(lastBody().surface_type).toBe("main_wing");
  });

  it("shows the backend detail message when creation fails", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 422, text: async () => JSON.stringify({ detail: "Aeroplane already has a main wing" }) });
    render(<CreateWingDialog open onClose={vi.fn()} aeroplaneId="a1" />);
    fireEvent.change(screen.getByLabelText("Wing name"), { target: { value: "w" } });
    fireEvent.click(screen.getByRole("button", { name: "Create", hidden: true }));
    expect(await screen.findByText(/Aeroplane already has a main wing/)).toBeTruthy();
  });
});

describe("WingSurfaceTypePanel", () => {
  const all = [
    { name: "main", surface_type: "main_wing" as const },
    { name: "htail", surface_type: "horizontal_tail" as const },
  ];

  it("shows no marker for a confirmed role", () => {
    render(
      <WingSurfaceTypePanel aeroplaneId="a1" wing={{ name: "htail", surface_type: "horizontal_tail", surface_type_inferred: false }} allWings={all} />,
    );
    expect(screen.queryByTestId("surface-type-proposed")).toBeNull();
    expect(screen.queryByRole("button", { name: "Confirm" })).toBeNull();
  });

  it("marks an inferred role and Confirm PATCHes the current value", async () => {
    render(
      <WingSurfaceTypePanel aeroplaneId="a1" wing={{ name: "htail", surface_type: "horizontal_tail", surface_type_inferred: true }} allWings={all} />,
    );
    expect(screen.getByTestId("surface-type-proposed").getAttribute("title")).toMatch(/proposed/i);
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://api/v2/aeroplanes/a1/wings/htail/surface-type");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body)).toEqual({ surface_type: "horizontal_tail" });
  });

  it("requires the swap selector when taking over main_wing and sends former_main_becomes", async () => {
    render(
      <WingSurfaceTypePanel aeroplaneId="a1" wing={{ name: "htail", surface_type: "horizontal_tail", surface_type_inferred: false }} allWings={all} />,
    );
    expect(screen.queryByLabelText(/becomes/)).toBeNull();
    fireEvent.change(screen.getByLabelText("Wing role"), { target: { value: "main_wing" } });
    const former = screen.getByLabelText(/Current main wing \(main\) becomes/) as HTMLSelectElement;
    expect(Array.from(former.options).some((o) => o.value === "main_wing")).toBe(false);
    fireEvent.change(former, { target: { value: "canard" } });
    fireEvent.click(screen.getByRole("button", { name: "Save role" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      surface_type: "main_wing",
      former_main_becomes: "canard",
    });
  });

  it("shows the backend 422 detail inline", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 422,
      text: async () => JSON.stringify({ detail: "Cannot retype the only main wing" }),
    });
    render(
      <WingSurfaceTypePanel aeroplaneId="a1" wing={{ name: "main", surface_type: "main_wing", surface_type_inferred: false }} allWings={all} />,
    );
    fireEvent.change(screen.getByLabelText("Wing role"), { target: { value: "canard" } });
    fireEvent.click(screen.getByRole("button", { name: "Save role" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Cannot retype the only main wing");
  });
});
