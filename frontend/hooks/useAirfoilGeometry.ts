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
        const res = await fetch(
          `${API_BASE}/airfoils/${encodeURIComponent(airfoilName)}/datfile`,
        );
        if (!res.ok) throw new Error(`Failed to load airfoil: ${res.status}`);
        const data = await res.json();
        // data has: { airfoil_name, file_name, datfile_content: string }
        const parsed = parseSeligDat(data.datfile_content);
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

export function parseSeligDat(content: string): AirfoilGeometry {
  const lines = content.trim().split("\n");
  // First line is name, rest are coordinates
  const coords: [number, number][] = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].trim().split(/\s+/);
    if (parts.length >= 2) {
      const x = parseFloat(parts[0]);
      const y = parseFloat(parts[1]);
      if (!isNaN(x) && !isNaN(y)) coords.push([x, y]);
    }
  }

  // Find LE (minimum x) to split upper/lower
  let leIdx = 0;
  let minX = Infinity;
  for (let i = 0; i < coords.length; i++) {
    if (coords[i][0] < minX) {
      minX = coords[i][0];
      leIdx = i;
    }
  }

  const upper = coords.slice(0, leIdx + 1); // TE->LE (x decreasing)
  const lower = coords.slice(leIdx); // LE->TE (x increasing)

  // Compute thickness and camber at sampled x positions
  let maxThickness = 0;
  let maxCamber = 0;
  let maxThicknessX = 0.3;
  const sampleXs = Array.from({ length: 50 }, (_, i) => i / 49); // 0 to 1

  for (const x of sampleXs) {
    const yUpper = interpolateY(upper, x);
    const yLower = interpolateY(lower, x);
    if (yUpper !== null && yLower !== null) {
      const thickness = yUpper - yLower;
      const camber = (yUpper + yLower) / 2;
      if (thickness > maxThickness) {
        maxThickness = thickness;
        maxThicknessX = x;
      }
      if (Math.abs(camber) > Math.abs(maxCamber)) maxCamber = camber;
    }
  }

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
