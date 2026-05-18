/**
 * Hard-coded icosahedron geometry for the stability overlay markers.
 *
 * A bare icosahedron (12 verts, 20 faces) reads cleanly as a sphere at
 * typical CAD-viewer distances. No subdivision needed.
 *
 * Used as `mesh3d` markers (world-units) instead of `scatter3d` with
 * pixel-sized `marker.size` — so the markers scale naturally with zoom
 * and never visually overlap.
 */

// Golden ratio — defines an icosahedron in (±1, ±PHI, 0) permutations.
const PHI = (1 + Math.sqrt(5)) / 2;
const NORM = Math.sqrt(1 + PHI * PHI);

/** 12 unit-sphere vertices (icosahedron). */
const ICO_VERTS: ReadonlyArray<readonly [number, number, number]> = (
  [
    [-1, PHI, 0],
    [1, PHI, 0],
    [-1, -PHI, 0],
    [1, -PHI, 0],
    [0, -1, PHI],
    [0, 1, PHI],
    [0, -1, -PHI],
    [0, 1, -PHI],
    [PHI, 0, -1],
    [PHI, 0, 1],
    [-PHI, 0, -1],
    [-PHI, 0, 1],
  ] as ReadonlyArray<readonly [number, number, number]>
).map(([x, y, z]) => [x / NORM, y / NORM, z / NORM] as const);

/** 20 triangle indices (CCW winding). */
const ICO_FACES: ReadonlyArray<readonly [number, number, number]> = [
  [0, 11, 5],
  [0, 5, 1],
  [0, 1, 7],
  [0, 7, 10],
  [0, 10, 11],
  [1, 5, 9],
  [5, 11, 4],
  [11, 10, 2],
  [10, 7, 6],
  [7, 1, 8],
  [3, 9, 4],
  [3, 4, 2],
  [3, 2, 6],
  [3, 6, 8],
  [3, 8, 9],
  [4, 9, 5],
  [2, 4, 11],
  [6, 2, 10],
  [8, 6, 7],
  [9, 8, 1],
];

export interface SphereMesh {
  x: number[];
  y: number[];
  z: number[];
  i: number[];
  j: number[];
  k: number[];
}

/**
 * Build an icosphere centred at `(cx, cy, cz)` with the given `radius`.
 * Returns coordinate arrays and triangle index arrays in the shape
 * expected by Plotly `mesh3d` traces.
 *
 * Note: name uses "icosphere" for its sphere-marker role; the returned mesh
 * is actually a bare icosahedron (12 verts, 20 faces) — no geodesic subdivision.
 */
export function makeIcosphere(
  cx: number,
  cy: number,
  cz: number,
  radius: number,
): SphereMesh {
  const x = ICO_VERTS.map((v) => cx + v[0] * radius);
  const y = ICO_VERTS.map((v) => cy + v[1] * radius);
  const z = ICO_VERTS.map((v) => cz + v[2] * radius);
  const i = ICO_FACES.map((f) => f[0]);
  const j = ICO_FACES.map((f) => f[1]);
  const k = ICO_FACES.map((f) => f[2]);
  return { x, y, z, i, j, k };
}
