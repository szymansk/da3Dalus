"use client";

import { useState, useCallback } from "react";
import { API_BASE } from "@/lib/fetcher";

interface StlExportState {
  stlUrl: string | null;
  isExporting: boolean;
  progress: string;
  error: string | null;
}

export function useStlExport(aeroplaneId: string | null, wingName: string | null) {
  const [state, setState] = useState<StlExportState>({
    stlUrl: null,
    isExporting: false,
    progress: "",
    error: null,
  });

  const triggerExport = useCallback(async () => {
    if (!aeroplaneId || !wingName) return;

    setState({ stlUrl: null, isExporting: true, progress: "Starting export…", error: null });

    try {
      console.log("[useStlExport] Starting export for", wingName);
      // 1. Trigger the STL export task
      const encodedWing = encodeURIComponent(wingName);
      const postRes = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodedWing}/wing_loft/stl`,
        { method: "POST" },
      );
      if (!postRes.ok) {
        throw new Error(`Export trigger failed: ${postRes.status}`);
      }

      // 2. Poll for completion
      setState((s) => ({ ...s, progress: "Generating geometry…" }));
      const deadline = Date.now() + 120_000; // 2 min timeout
      while (Date.now() < deadline) {
        const statusRes = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}/status`);
        if (!statusRes.ok) throw new Error(`Status check failed: ${statusRes.status}`);
        const statusData = await statusRes.json();

        if (statusData.status === "SUCCESS") {
          // 3. Get the ZIP URL
          const zipRes = await fetch(
            `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodedWing}/wing_loft/stl/zip`,
          );
          if (!zipRes.ok) throw new Error(`ZIP metadata failed: ${zipRes.status}`);
          const zipMeta = await zipRes.json();

          // 4. Download ZIP and extract first STL
          const zipUrl = zipMeta.url.startsWith("http")
            ? zipMeta.url
            : `${API_BASE}${zipMeta.url}`;
          const zipBlobRes = await fetch(zipUrl);
          if (!zipBlobRes.ok) throw new Error(`ZIP download failed: ${zipBlobRes.status}`);
          const zipBlob = await zipBlobRes.blob();

          // Use JSZip or manual extraction — for MVP, serve the whole blob
          // as an STL (the ZIP typically contains a single STL file)
          // Actually, we need to extract. Use a simple approach:
          const { BlobReader, BlobWriter, ZipReader } = await import("@zip.js/zip.js");
          const reader = new ZipReader(new BlobReader(zipBlob));
          const entries = await reader.getEntries();
          const stlEntry = entries.find((e) => e.filename.endsWith(".stl"));

          if (!stlEntry) {
            throw new Error("No STL file found in export ZIP");
          }

          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const stlBlob: Blob = await (stlEntry as any).getData(new BlobWriter());
          await reader.close();

          const blobUrl = URL.createObjectURL(stlBlob);
          setState({ stlUrl: blobUrl, isExporting: false, progress: "", error: null });
          return;
        }

        if (statusData.status === "FAILURE") {
          throw new Error(statusData.message || "Export failed");
        }

        await new Promise((r) => setTimeout(r, 500));
      }

      throw new Error("Export timed out after 2 minutes");
    } catch (err) {
      console.error("[useStlExport] Error:", err);
      setState({
        stlUrl: null,
        isExporting: false,
        progress: "",
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }, [aeroplaneId, wingName]);

  return { ...state, triggerExport };
}
