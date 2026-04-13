"use client";

import { useEffect, useRef, useState } from "react";

interface CadViewerProps {
  /** One or more tessellation results to render. Each is a single-wing
   *  tessellation in three-cad-viewer format: {data:{instances,shapes}, ...} */
  parts: Record<string, unknown>[];
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

/**
 * Wraps the three-cad-viewer library to render tessellated CAD geometry.
 *
 * Supports multiple parts via viewer.addPart() — each wing is added
 * incrementally instead of assembling one giant JSON payload.
 */
export function CadViewer({ parts }: CadViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!containerRef.current || parts.length === 0) return;
    let disposed = false;

    async function init() {
      try {
        setLoading(true);
        setError(null);

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const tcv = await import("three-cad-viewer") as any;
        if (disposed || !containerRef.current) return;

        const container = containerRef.current;

        // Cleanup previous viewer
        if (viewerRef.current) {
          try { (viewerRef.current as any).dispose?.(); } catch { /* ok */ }
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
          ambientIntensity: 1.0,
          directIntensity: 1.1,
          metalness: 0.3,
          roughness: 0.65,
          edgeColor: 0x707070,
          defaultOpacity: 1.0,
        };

        // Extract shapes from the first part and render it (initializes the scene)
        const first = parts[0] as {
          data?: { shapes?: Record<string, unknown>; instances?: Record<string, unknown>[] };
        };
        const firstShapes = first?.data?.shapes;
        const firstInstances = first?.data?.instances;
        if (!firstShapes) throw new Error("No shape data in tessellation result");

        if (firstInstances && Array.isArray(firstInstances)) {
          resolveRefs(firstShapes, firstInstances);
        }

        viewer.render(firstShapes, renderOptions, viewerOptions);

        // Add remaining parts incrementally via addPart()
        for (let i = 1; i < parts.length; i++) {
          const part = parts[i] as {
            data?: { shapes?: Record<string, unknown>; instances?: Record<string, unknown>[] };
          };
          const shapes = part?.data?.shapes;
          const instances = part?.data?.instances;
          if (!shapes) continue;

          if (instances && Array.isArray(instances)) {
            resolveRefs(shapes, instances);
          }

          try {
            // addPart requires a parent path — use the root of the first shape
            const rootId = (firstShapes as any).id || "/Group";
            viewer.addPart(rootId, shapes, { skipBounds: true });
          } catch (err) {
            console.warn(`[CadViewer] addPart for part ${i} failed:`, err);
          }
        }

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
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
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
