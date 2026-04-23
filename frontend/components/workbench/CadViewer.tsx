"use client";

import { useEffect, useRef, useState } from "react";

interface CadViewerProps {
  /** One or more tessellation results to render. Each is a single-wing
   *  tessellation in three-cad-viewer format: {data:{instances,shapes}, ...} */
  parts: Record<string, unknown>[];
}

interface PartData {
  data?: { shapes?: Record<string, unknown>; instances?: Record<string, unknown>[] };
}

function resolveRefs(
  node: Record<string, unknown>,
  instances: Record<string, unknown>[],
) {
  if (node.shape && typeof node.shape === "object") {
    const s = node.shape as Record<string, unknown>;
    if ("ref" in s && typeof s.ref === "number") {
      node.shape = instances[s.ref as number];
    }
  }
  if (Array.isArray(node.parts)) {
    for (const part of node.parts) {
      if (part && typeof part === "object") {
        resolveRefs(part as Record<string, unknown>, instances);
      }
    }
  }
}

/** Deep-clone shapes and resolve instance refs for a single part. Returns null if no shapes. */
function preparePartShapes(part: PartData): Record<string, unknown> | null {
  const shapes = part?.data?.shapes;
  if (!shapes) return null;
  const copy = structuredClone(shapes);
  const instances = part?.data?.instances;
  if (Array.isArray(instances)) {
    resolveRefs(copy, instances);
  }
  return copy;
}

/** Add remaining parts to an already-initialised viewer. */
function addRemainingParts(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  viewer: any,
  parts: Record<string, unknown>[],
  rootId: string,
): void {
  for (let i = 1; i < parts.length; i++) {
    const shapes = preparePartShapes(parts[i] as PartData);
    if (!shapes) continue;
    try {
      viewer.addPart(rootId, shapes, { skipBounds: true });
    } catch (err) {
      console.warn(`[CadViewer] addPart for part ${i} failed:`, err);
    }
  }
}

/**
 * Wraps the three-cad-viewer library to render tessellated CAD geometry.
 *
 * Supports multiple parts via viewer.addPart() — each wing is added
 * incrementally instead of assembling one giant JSON payload.
 */
export function CadViewer({ parts }: Readonly<CadViewerProps>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const containerNode = containerRef.current;
    if (!containerNode || parts.length === 0) return;
    let disposed = false;

    async function init() {
      try {
        setLoading(true);
        setError(null);

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const tcv = await import("three-cad-viewer") as any;
        if (disposed || !containerNode) return;

        const container = containerNode;

        // Cleanup previous viewer
        if (viewerRef.current) {
          try { (viewerRef.current as { dispose?: () => void }).dispose?.(); } catch { /* ok */ }
        }
        container.innerHTML = "";

        const w = container.clientWidth || 800;
        const h = container.clientHeight || 500;

        const display = new tcv.Display(container, {
          cadWidth: w,
          height: h,
          treeWidth: 0,
          theme: "dark",
          glass: false,
          tools: false,
        });

        const viewerOptions = { target: [0, 0, 0], up: "Z" };
        const viewer = new tcv.Viewer(display, viewerOptions, () => {});
        viewerRef.current = viewer;

        const renderOptions = {
          ambientIntensity: 1,
          directIntensity: 1.1,
          metalness: 0.3,
          roughness: 0.65,
          edgeColor: 0x707070,
          defaultOpacity: 1,
        };

        // Extract shapes from the first part and render it (initializes the scene)
        const firstShapesCopy = preparePartShapes(parts[0] as PartData);
        if (!firstShapesCopy) throw new Error("No shape data in tessellation result");

        viewer.render(firstShapesCopy, renderOptions, viewerOptions);

        // Add remaining parts incrementally via addPart()
        const rootId = (firstShapesCopy as { id?: string }).id || "/Group";
        addRemainingParts(viewer, parts, rootId);

        // Recompute bounds once after all parts are added
        if (parts.length > 1) {
          try { viewer.updateBounds(); } catch { /* ok */ }
        }

        setLoading(false);
      } catch (err) {
        console.error("[CadViewer] Error:", err);
        if (!disposed) {
          setError(err instanceof Error ? err.message : String(err));
          setLoading(false);
        }
      }
    }

    init();

    return () => {
      disposed = true;
      if (viewerRef.current) {
        try { (viewerRef.current as { dispose?: () => void }).dispose?.(); } catch { /* ok */ }
        viewerRef.current = null;
      }
      if (containerNode) {
        containerNode.innerHTML = "";
      }
    };
  }, [parts]);

  if (error) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="flex flex-col items-center gap-2">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-destructive">
            Viewer Error
          </span>
          <span className="max-w-md text-center text-[12px] text-muted-foreground">{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      {loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-card-muted/80">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
            Initializing 3D viewer…
          </span>
        </div>
      )}
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
}
