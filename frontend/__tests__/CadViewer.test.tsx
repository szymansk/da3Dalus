/**
 * Unit test for CadViewer initialization.
 *
 * Mocks three-cad-viewer to verify that Display and Viewer are
 * constructed with the correct options. This catches the regression
 * where `glass: false` and `tools: false` were accidentally removed.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, act } from "@testing-library/react";
import React from "react";

// Track constructor calls
const mockRender = vi.fn();
const mockDispose = vi.fn();
let lastDisplayOptions: Record<string, unknown> | null = null;
let lastViewerOptions: Record<string, unknown> | null = null;

vi.mock("three-cad-viewer", () => ({
  Display: class MockDisplay {
    constructor(_container: HTMLElement, options: Record<string, unknown>) {
      lastDisplayOptions = options;
    }
    dispose() {
      mockDispose();
    }
  },
  Viewer: class MockViewer {
    constructor(
      _display: unknown,
      options: Record<string, unknown>,
      _cb: () => void,
    ) {
      lastViewerOptions = options;
    }
    render(...args: unknown[]) {
      mockRender(...args);
    }
    dispose() {
      mockDispose();
    }
  },
}));

// Import AFTER mock is set up
const { CadViewer } = await import(
  "../components/workbench/CadViewer"
);

const SAMPLE_SHAPES = {
  data: {
    shapes: {
      version: 3,
      name: "test",
      id: "/test",
      parts: [
        {
          id: "/test/wing",
          type: "shapes",
          subtype: "solid",
          name: "wing",
          shape: { vertices: [0, 0, 0], triangles: [0], normals: [0, 0, 1], edges: [] },
          state: [1, 1],
          color: "#FF8400",
          alpha: 1.0,
          loc: [[0, 0, 0], [0, 0, 0, 1]],
        },
      ],
      loc: [[0, 0, 0], [0, 0, 0, 1]],
      bb: { xmin: 0, ymin: 0, zmin: 0, xmax: 1, ymax: 1, zmax: 1 },
    },
    instances: [],
  },
  type: "data",
  config: { theme: "dark" },
  count: 1,
};

describe("CadViewer", () => {
  beforeEach(() => {
    lastDisplayOptions = null;
    lastViewerOptions = null;
    mockRender.mockClear();
    mockDispose.mockClear();
  });

  it("passes glass:false and tools:false to Display constructor", async () => {
    await act(async () => {
      render(<CadViewer parts={[SAMPLE_SHAPES as unknown as Record<string, unknown>]} />);
    });
    // Wait for dynamic import + init
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(lastDisplayOptions).not.toBeNull();
    expect(lastDisplayOptions!.glass).toBe(false);
    expect(lastDisplayOptions!.tools).toBe(false);
  });

  it("passes theme:dark and treeWidth:0 to Display", async () => {
    await act(async () => {
      render(<CadViewer parts={[SAMPLE_SHAPES as unknown as Record<string, unknown>]} />);
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(lastDisplayOptions!.theme).toBe("dark");
    expect(lastDisplayOptions!.treeWidth).toBe(0);
  });

  it("passes target and up to Viewer constructor", async () => {
    await act(async () => {
      render(<CadViewer parts={[SAMPLE_SHAPES as unknown as Record<string, unknown>]} />);
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(lastViewerOptions).not.toBeNull();
    expect(lastViewerOptions!.target).toEqual([0, 0, 0]);
    expect(lastViewerOptions!.up).toBe("Z");
  });

  it("calls viewer.render() with shapes data", async () => {
    await act(async () => {
      render(<CadViewer parts={[SAMPLE_SHAPES as unknown as Record<string, unknown>]} />);
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(mockRender).toHaveBeenCalledTimes(1);
    const [shapes, renderOpts] = mockRender.mock.calls[0];
    expect(shapes.version).toBe(3);
    expect(shapes.parts).toHaveLength(1);
    expect(renderOpts.ambientIntensity).toBe(1.0);
    expect(renderOpts.edgeColor).toBe(0x707070);
  });

  it("does not render when parts is empty", async () => {
    await act(async () => {
      render(<CadViewer parts={[]} />);
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(mockRender).not.toHaveBeenCalled();
    expect(lastDisplayOptions).toBeNull();
  });
});
