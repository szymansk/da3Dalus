/**
 * Unit tests for ImportOpenVspButton (gh-646).
 */

import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ImportOpenVspButton from "@/components/workbench/ImportOpenVspButton";

describe("ImportOpenVspButton", () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the upload button with the default label", () => {
    render(<ImportOpenVspButton />);
    expect(screen.getByTestId("openvsp-import-button")).toHaveTextContent(
      /Import OpenVSP/i,
    );
  });

  it("rejects non-.vsp3 files via onError", async () => {
    const onError = vi.fn();
    render(<ImportOpenVspButton onError={onError} />);
    const input = screen.getByTestId(
      "openvsp-file-input",
    ) as HTMLInputElement;
    const txt = new File(["x"], "notes.txt", { type: "text/plain" });
    // Bypass the input's accept filter (userEvent.upload honours it) by
    // dispatching a change event directly — the handler must still reject.
    Object.defineProperty(input, "files", { value: [txt], configurable: true });
    fireEvent.change(input);
    // The handler is sync up to the .vsp3 check, so onError fires now.
    expect(onError).toHaveBeenCalledWith(expect.stringContaining(".vsp3"));
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("POSTs the .vsp3 and calls onImported with the response", async () => {
    const fakeResponse = {
      aeroplane_uuid: "uuid-1",
      aeroplane_name: "OneRAM6",
      n_wings: 1,
      n_fuselages: 0,
      n_weight_items: 0,
      warnings: [],
      lossy_components: [],
    };
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => fakeResponse,
    } as Response);
    const onImported = vi.fn();
    render(<ImportOpenVspButton onImported={onImported} />);
    const input = screen.getByTestId(
      "openvsp-file-input",
    ) as HTMLInputElement;
    const f = new File(["<vsp3/>"], "test.vsp3", {
      type: "application/octet-stream",
    });
    await userEvent.upload(input, f);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v2/import/openvsp"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(onImported).toHaveBeenCalledWith(fakeResponse);
  });

  it("forwards backend error detail to onError", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ detail: "openvsp not installed" }),
    } as Response);
    const onError = vi.fn();
    render(<ImportOpenVspButton onError={onError} />);
    const input = screen.getByTestId(
      "openvsp-file-input",
    ) as HTMLInputElement;
    const f = new File(["x"], "x.vsp3", {
      type: "application/octet-stream",
    });
    await userEvent.upload(input, f);
    expect(onError).toHaveBeenCalledWith("openvsp not installed");
  });
});
