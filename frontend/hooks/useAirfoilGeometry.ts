"use client";

import { useState, useEffect } from "react";
import { API_BASE } from "@/lib/fetcher";

export interface AirfoilGeometry {
  upper: [number, number][]; // [x, y] pairs, TE->LE
  lower: [number, number][]; // [x, y] pairs, LE->TE
  maxThicknessPct: number;
  maxCamberPct: number;
  maxThicknessX: number; // x-position of max thickness
}

export function useAirfoilGeometry(airfoilName: string | null) {
  const [geometry, setGeometry] = useState<AirfoilGeometry | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!airfoilName) {
      setGeometry(null);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    (async () => {
      try {
        // Step 1: Get download URL from backend
        const metaRes = await fetch(
          `${API_BASE}/airfoils/${encodeURIComponent(airfoilName)}/datfile`,
        );
        if (!metaRes.ok) throw new Error(`Failed to load airfoil: ${metaRes.status}`);
        const meta = await metaRes.json();
        // meta has: { url, airfoil_name, file_name, ... }

        // Step 2: Fetch actual .dat content from the URL
        const datUrl = meta.url.startsWith("http") ? meta.url : `${API_BASE}${meta.url}`;
        const datRes = await fetch(datUrl);
        if (!datRes.ok) throw new Error(`Failed to download .dat file: ${datRes.status}`);
        const datContent = await datRes.text();

        const parsed = parseSeligDat(datContent);
        if (!cancelled) setGeometry(parsed);
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [airfoilName]);

  return { geometry, isLoading, error };
}

/** Parse coordinate lines (skip header) into [x, y] pairs. */
function parseCoordinates(lines: string[]): [number, number][] {
  const coords: [number, number][] = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].trim().split(/\s+/);
    if (parts.length < 2) continue;
    const x = Number.parseFloat(parts[0]);
    const y = Number.parseFloat(parts[1]);
    if (!Number.isNaN(x) && !Number.isNaN(y)) coords.push([x, y]);
  }
  return coords;
}

/** Find the leading-edge index (minimum x). */
function findLeadingEdgeIndex(coords: [number, number][]): number {
  let leIdx = 0;
  let minX = Infinity;
  for (let i = 0; i < coords.length; i++) {
    if (coords[i][0] < minX) {
      minX = coords[i][0];
      leIdx = i;
    }
  }
  return leIdx;
}

/** Compute max thickness, camber, and thickness x-position from upper/lower surfaces. */
function computeThicknessAndCamber(
  upper: [number, number][],
  lower: [number, number][],
): { maxThickness: number; maxCamber: number; maxThicknessX: number } {
  let maxThickness = 0;
  let maxCamber = 0;
  let maxThicknessX = 0.3;
  const sampleXs = Array.from({ length: 50 }, (_, i) => i / 49);

  for (const x of sampleXs) {
    const yUpper = interpolateY(upper, x);
    const yLower = interpolateY(lower, x);
    if (yUpper === null || yLower === null) continue;

    const thickness = yUpper - yLower;
    const camber = (yUpper + yLower) / 2;
    if (thickness > maxThickness) {
      maxThickness = thickness;
      maxThicknessX = x;
    }
    if (Math.abs(camber) > Math.abs(maxCamber)) maxCamber = camber;
  }

  return { maxThickness, maxCamber, maxThicknessX };
}

export function parseSeligDat(content: string): AirfoilGeometry {
  const lines = content.trim().split("\n");
  const coords = parseCoordinates(lines);
  const leIdx = findLeadingEdgeIndex(coords);

  const upper = coords.slice(0, leIdx + 1); // TE->LE (x decreasing)
  const lower = coords.slice(leIdx); // LE->TE (x increasing)

  const { maxThickness, maxCamber, maxThicknessX } =
    computeThicknessAndCamber(upper, lower);

  return {
    upper,
    lower,
    maxThicknessPct: Math.round(maxThickness * 1000) / 10,
    maxCamberPct: Math.round(Math.abs(maxCamber) * 1000) / 10,
    maxThicknessX,
  };
}

export function interpolateY(
  surface: [number, number][],
  targetX: number,
): number | null {
  for (let i = 0; i < surface.length - 1; i++) {
    const [x0, y0] = surface[i];
    const [x1, y1] = surface[i + 1];
    const xMin = Math.min(x0, x1);
    const xMax = Math.max(x0, x1);
    if (targetX >= xMin && targetX <= xMax && xMax > xMin) {
      const t = (targetX - x0) / (x1 - x0);
      return y0 + t * (y1 - y0);
    }
  }
  return null;
}
