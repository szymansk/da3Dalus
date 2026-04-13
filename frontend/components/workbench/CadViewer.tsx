"use client";

import { useEffect, useRef, useState } from "react";

interface CadViewerProps {
  /** Tessellation data in three-cad-viewer format: {data:{instances,shapes}, config, count} */
  data: Record<string, unknown> | null;
}

/**
 * Wraps the three-cad-viewer library to render tessellated CAD geometry.
 * Uses the same viewer as the VS Code OCP CAD Viewer extension.
 */
export function CadViewer({ data }: CadViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!containerRef.current || !data) return;
    let disposed = false;

    async function init() {
      try {
        setLoading(true);
        setError(null);

        const tcv = await import("three-cad-viewer");
        if (disposed || !containerRef.current) return;

        const container = containerRef.current;

        // Cleanup previous viewer
        if (viewerRef.current) {
          try {
            (viewerRef.current as { dispose?: () => void }).dispose?.();
          } catch { /* ignore */ }
        }
        container.innerHTML = "";

        const w = container.clientWidth || 800;
        const h = container.clientHeight || 500;

        // Create Display (layout container)
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const display = new tcv.Display(container, {
          cadWidth: w,
          height: h,
          treeWidth: 0,
          theme: "dark",
          glass: false,
          tools: false,
        } as any);

        // Create Viewer (3D renderer)
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const viewer = new (tcv as any).Viewer(
          display,
          { target: [0, 0, 0], up: "Z" },
          () => {},
        );
        viewerRef.current = viewer;

        // Extract shapes from the tessellation data
        const tessData = data as {
          data?: { shapes?: Record<string, unknown>; instances?: Record<string, unknown>[] };
          config?: Record<string, unknown>;
        };

        const shapes = tessData?.data?.shapes;
        const instances = tessData?.data?.instances;
        if (!shapes) {
          throw new Error("No shape data in tessellation result");
        }

        // Resolve instance references: shapes may have {ref: N} instead
        // of inline geometry. Replace refs with actual instance data.
        if (instances && Array.isArray(instances)) {
          const inst = instances; // narrow for closure
          function resolveRefs(node: Record<string, unknown>) {
            if (node.shape && typeof node.shape === "object") {
              const shapeObj = node.shape as Record<string, unknown>;
              if ("ref" in shapeObj && typeof shapeObj.ref === "number") {
                node.shape = inst[shapeObj.ref as number];
              }
            }
            if (Array.isArray(node.parts)) {
              for (const part of node.parts) {
                if (part && typeof part === "object") {
                  resolveRefs(part as Record<string, unknown>);
                }
              }
            }
          }
          resolveRefs(shapes);
        }

        // Render the shapes
        viewer.render(
          shapes,
          {
            ambientIntensity: 1.0,
            directIntensity: 1.1,
            metalness: 0.3,
            roughness: 0.65,
            edgeColor: 0x707070,
            defaultOpacity: 1.0,
          },
          {},
        );

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
        try {
          (viewerRef.current as { dispose?: () => void }).dispose?.();
        } catch { /* ignore */ }
        viewerRef.current = null;
      }
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }
    };
  }, [data]);

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
