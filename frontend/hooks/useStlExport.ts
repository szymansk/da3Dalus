"use client";

import { useState, useCallback } from "react";
import { API_BASE } from "@/lib/fetcher";

interface StlExportState {
  stlUrl: string | null;
  isExporting: boolean;
  progress: string;
  error: string | null;
}

/** Trigger the STL export task on the backend. */
async function triggerStlTask(aeroplaneId: string, encodedWing: string): Promise<void> {
  const postRes = await fetch(
    `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodedWing}/wing_loft/stl`,
    { method: "POST" },
  );
  if (!postRes.ok) {
    throw new Error(`Export trigger failed: ${postRes.status}`);
  }
}

/** Poll the status endpoint until SUCCESS or FAILURE (2 min timeout). */
async function pollExportStatus(aeroplaneId: string): Promise<void> {
  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    const statusRes = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}/status`);
    if (!statusRes.ok) throw new Error(`Status check failed: ${statusRes.status}`);
    const statusData = await statusRes.json();

    if (statusData.status === "SUCCESS") return;
    if (statusData.status === "FAILURE") {
      throw new Error(statusData.message || "Export failed");
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("Export timed out after 2 minutes");
}

/** Download the ZIP, extract the first .stl entry, and return a blob URL. */
async function downloadAndExtractStl(
  aeroplaneId: string,
  encodedWing: string,
): Promise<string> {
  const zipRes = await fetch(
    `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodedWing}/wing_loft/stl/zip`,
  );
  if (!zipRes.ok) throw new Error(`ZIP metadata failed: ${zipRes.status}`);
  const zipMeta = await zipRes.json();

  const zipUrl = zipMeta.url.startsWith("http")
    ? zipMeta.url
    : `${API_BASE}${zipMeta.url}`;
  const zipBlobRes = await fetch(zipUrl);
  if (!zipBlobRes.ok) throw new Error(`ZIP download failed: ${zipBlobRes.status}`);
  const zipBlob = await zipBlobRes.blob();

  const { BlobReader, BlobWriter, ZipReader } = await import("@zip.js/zip.js");
  const reader = new ZipReader(new BlobReader(zipBlob));
  const entries = await reader.getEntries();
  const stlEntry = entries.find((e) => e.filename.endsWith(".stl"));

  if (!stlEntry) {
    throw new Error("No STL file found in export ZIP");
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const stlBlob = await (stlEntry as any).getData(new BlobWriter()) as Blob;
  await reader.close();

  return URL.createObjectURL(stlBlob);
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
      const encodedWing = encodeURIComponent(wingName);
      await triggerStlTask(aeroplaneId, encodedWing);

      setState((s) => ({ ...s, progress: "Generating geometry…" }));
      await pollExportStatus(aeroplaneId);

      const blobUrl = await downloadAndExtractStl(aeroplaneId, encodedWing);
      setState({ stlUrl: blobUrl, isExporting: false, progress: "", error: null });
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
