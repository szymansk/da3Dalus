/**
 * Unit tests for ImportOpenVspButton (gh-646, updated for the gh-737
 * streaming endpoint). The button now POSTs to
 * ``/api/v2/import/openvsp/stream`` and renders a progress bar driven
 * by SSE events; the helper below mocks fetch with a ReadableStream
 * body that emits the right SSE blocks.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ImportOpenVspButton from "@/components/workbench/ImportOpenVspButton";

/** Build a Response whose body streams the given SSE blocks. */
function mockSseResponse(blocks: string[], ok = true, status = 200): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const b of blocks) controller.enqueue(encoder.encode(b));
      controller.close();
    },
  });
  return {
    ok,
    status,
    body: stream,
    headers: new Headers({ "content-type": "text/event-stream" }),
    json: async () => ({}),
    text: async () => blocks.join(""),
  } as Response;
}

function sseBlock(event: string, data: Record<string, unknown>): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

const fakeCompleteResponse = {
  aeroplane_uuid: "uuid-1",
  aeroplane_name: "OneRAM6",
  n_wings: 1,
  n_fuselages: 0,
  n_weight_items: 0,
  warnings: [],
  lossy_components: [],
};

describe("ImportOpenVspButton (streaming)", () => {
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

  it("rejects non-.vsp3 files via onError before opening a stream", async () => {
    const onError = vi.fn();
    render(<ImportOpenVspButton onError={onError} />);
    const input = screen.getByTestId(
      "openvsp-file-input",
    ) as HTMLInputElement;
    const txt = new File(["x"], "notes.txt", { type: "text/plain" });
    Object.defineProperty(input, "files", { value: [txt], configurable: true });
    fireEvent.change(input);
    expect(onError).toHaveBeenCalledWith(expect.stringContaining(".vsp3"));
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("POSTs to the streaming endpoint and resolves onImported on `complete`", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      mockSseResponse([
        sseBlock("progress", { step: "parsing", pct: 10, detail: "Reading" }),
        sseBlock("complete", fakeCompleteResponse),
      ]),
    );
    const onImported = vi.fn();
    render(<ImportOpenVspButton onImported={onImported} />);
    const input = screen.getByTestId(
      "openvsp-file-input",
    ) as HTMLInputElement;
    const f = new File(["<vsp3/>"], "test.vsp3", {
      type: "application/octet-stream",
    });
    await userEvent.upload(input, f);
    await waitFor(() =>
      expect(onImported).toHaveBeenCalledWith(fakeCompleteResponse),
    );
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v2/import/openvsp/stream"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("forwards backend error events to onError", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      mockSseResponse([
        sseBlock("error", { status: 503, detail: "openvsp not installed" }),
      ]),
    );
    const onError = vi.fn();
    render(<ImportOpenVspButton onError={onError} />);
    const input = screen.getByTestId(
      "openvsp-file-input",
    ) as HTMLInputElement;
    const f = new File(["x"], "x.vsp3", {
      type: "application/octet-stream",
    });
    await userEvent.upload(input, f);
    await waitFor(() =>
      expect(onError).toHaveBeenCalledWith(
        expect.stringContaining("openvsp not installed"),
      ),
    );
  });

  it("appends ?name= when a customName is supplied", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      mockSseResponse([
        sseBlock("complete", { ...fakeCompleteResponse, aeroplane_name: "Cessna 172" }),
      ]),
    );
    render(<ImportOpenVspButton customName="Cessna 172" />);
    const input = screen.getByTestId(
      "openvsp-file-input",
    ) as HTMLInputElement;
    const f = new File(["<vsp3/>"], "x.vsp3", {
      type: "application/octet-stream",
    });
    await userEvent.upload(input, f);
    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledTimes(1),
    );
    const calledUrl = vi.mocked(global.fetch).mock.calls[0][0] as string;
    // URLSearchParams encodes spaces as '+'.
    expect(calledUrl).toMatch(/[?&]name=Cessna\+172\b/);
  });

  it("omits ?name= when customName is empty or whitespace", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      mockSseResponse([sseBlock("complete", fakeCompleteResponse)]),
    );
    render(<ImportOpenVspButton customName="   " />);
    const input = screen.getByTestId(
      "openvsp-file-input",
    ) as HTMLInputElement;
    const f = new File(["<vsp3/>"], "x.vsp3", {
      type: "application/octet-stream",
    });
    await userEvent.upload(input, f);
    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledTimes(1),
    );
    const calledUrl = vi.mocked(global.fetch).mock.calls[0][0] as string;
    expect(calledUrl).not.toMatch(/[?&]name=/);
  });

  it("combines customName with a scaleOption query param", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      mockSseResponse([sseBlock("complete", fakeCompleteResponse)]),
    );
    render(
      <ImportOpenVspButton
        customName="RV-7"
        scaleOption={{ mode: "scale_factor", scale_factor: 0.5 }}
      />,
    );
    const input = screen.getByTestId(
      "openvsp-file-input",
    ) as HTMLInputElement;
    const f = new File(["<vsp3/>"], "x.vsp3", {
      type: "application/octet-stream",
    });
    await userEvent.upload(input, f);
    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledTimes(1),
    );
    const calledUrl = vi.mocked(global.fetch).mock.calls[0][0] as string;
    expect(calledUrl).toMatch(/scale_factor=0\.5/);
    expect(calledUrl).toMatch(/name=RV-7/);
  });

  it("renders the progress bar while the stream is in flight", async () => {
    // Build a stream that only emits a progress event and never closes
    // so we can observe the bar in the rendered tree before completion.
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          encoder.encode(
            sseBlock("progress", { step: "parsing", pct: 42, detail: "Reading .vsp3" }),
          ),
        );
        // Don't close — leaves the stream "in flight" indefinitely.
      },
    });
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
      body: stream,
      headers: new Headers({ "content-type": "text/event-stream" }),
      json: async () => ({}),
      text: async () => "",
    } as Response);

    render(<ImportOpenVspButton />);
    const input = screen.getByTestId(
      "openvsp-file-input",
    ) as HTMLInputElement;
    const f = new File(["x"], "x.vsp3", { type: "application/octet-stream" });
    await userEvent.upload(input, f);

    await waitFor(() =>
      expect(screen.getByTestId("openvsp-import-progress")).toBeInTheDocument(),
    );
    await waitFor(() =>
      expect(screen.getByTestId("openvsp-import-progress-detail")).toHaveTextContent(
        "Reading .vsp3",
      ),
    );
    expect(screen.queryByTestId("openvsp-import-button")).not.toBeInTheDocument();
  });
});
