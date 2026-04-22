"use client";

import { useEffect, useRef, useState } from "react";
import type { Wing, XSec } from "@/hooks/useWings";
import type { Fuselage } from "@/hooks/useFuselage";
import { API_BASE } from "@/lib/fetcher";

interface WingOutlineViewerProps {
  wings: Wing[];
  fuselages: Fuselage[];
  visibleWings: Set<string>;
  visibleFuselages: Set<string>;
  selectedXsecIndex?: number | null;
  selectedWing?: string | null;
  selectedFuselage?: string | null;
  selectedFuselageXsecIndex?: number | null;
}

// ── Airfoil coordinate cache ─────────────────────────────────────

interface AirfoilCoords {
  x: number[]; y: number[];
  upper_x: number[]; upper_y: number[];
  lower_x: number[]; lower_y: number[];
  camber_x: number[]; camber_y: number[];
}

const airfoilCache: Record<string, AirfoilCoords | null> = {};

async function fetchAirfoilCoords(airfoilName: string): Promise<AirfoilCoords | null> {
  const stem = airfoilName.replace(/\.dat$/i, "").split("/").pop() ?? airfoilName;
  if (stem in airfoilCache) return airfoilCache[stem];
  try {
    const res = await fetch(`${API_BASE}/airfoils/${encodeURIComponent(stem)}/coordinates`);
    if (!res.ok) { airfoilCache[stem] = null; return null; }
    const data = await res.json();
    airfoilCache[stem] = data;
    return data;
  } catch {
    airfoilCache[stem] = null;
    return null;
  }
}

// ── Geometry helpers ─────────────────────────────────────────────

/** Transform normalized airfoil coordinates to 3D position at a station.
 *  Applies twist (rotation around Y in XZ plane) and dihedral (rotation around X in YZ plane). */
function transformProfile(
  profileX: number[], profileY: number[],
  chord: number, twist: number, xyz_le: number[],
  dihedralRad = 0,
): { x: number[]; y: number[]; z: number[] } {
  const twistRad = (twist ?? 0) * Math.PI / 180;
  const cosT = Math.cos(twistRad);
  const sinT = Math.sin(twistRad);
  const cosD = Math.cos(dihedralRad);
  const sinD = Math.sin(dihedralRad);
  const [leX, leY, leZ] = xyz_le;
  const ax: number[] = [], ay: number[] = [], az: number[] = [];
  for (let i = 0; i < profileX.length; i++) {
    const px = profileX[i] * chord;
    const pz = profileY[i] * chord;
    // Apply twist (rotate in XZ plane around LE)
    const rx = px * cosT + pz * sinT;
    const rz = -px * sinT + pz * cosT;
    // Apply dihedral (rotate in YZ plane around LE)
    ax.push(leX + rx);
    ay.push(leY + rz * (-sinD));
    az.push(leZ + rz * cosD);
  }
  return { x: ax, y: ay, z: az };
}

/** Interpolate between two airfoil profiles at fraction t (0=a, 1=b).
 *  Resamples both to nPts stations and lerps y values. */
function lerpProfile(
  a: AirfoilCoords, b: AirfoilCoords, t: number, nPts = 60,
): { x: number[]; y: number[] } {
  const xs: number[] = [];
  const ys: number[] = [];
  for (let i = 0; i <= nPts; i++) {
    const xNorm = i / nPts;
    xs.push(xNorm);
    const ya = lerpLookup(a.x, a.y, xNorm);
    const yb = lerpLookup(b.x, b.y, xNorm);
    ys.push(ya * (1 - t) + yb * t);
  }
  return { x: xs, y: ys };
}

/** Interpolate camber lines similarly. */
function lerpCamber(
  a: AirfoilCoords, b: AirfoilCoords, t: number, nPts = 40,
): { x: number[]; y: number[] } {
  const xs: number[] = [], ys: number[] = [];
  for (let i = 0; i <= nPts; i++) {
    const xNorm = i / nPts;
    xs.push(xNorm);
    const ya = lerpLookup(a.camber_x, a.camber_y, xNorm);
    const yb = lerpLookup(b.camber_x, b.camber_y, xNorm);
    ys.push(ya * (1 - t) + yb * t);
  }
  return { x: xs, y: ys };
}

/** Linear interpolation lookup in sorted x/y arrays. */
function lerpLookup(xs: number[], ys: number[], target: number): number {
  if (xs.length === 0) return 0;
  if (target <= xs[0]) return ys[0];
  if (target >= xs[xs.length - 1]) return ys[ys.length - 1];
  for (let i = 1; i < xs.length; i++) {
    if (xs[i] >= target) {
      const frac = (target - xs[i - 1]) / (xs[i] - xs[i - 1] + 1e-12);
      return ys[i - 1] + frac * (ys[i] - ys[i - 1]);
    }
  }
  return ys[ys.length - 1];
}

/** Linearly interpolate two xsec stations at fraction t. */
function lerpStation(a: XSec, b: XSec, t: number): { xyz_le: number[]; chord: number; twist: number } {
  return {
    xyz_le: a.xyz_le.map((v, i) => v + (b.xyz_le[i] - v) * t),
    chord: a.chord + (b.chord - a.chord) * t,
    twist: (a.twist ?? 0) + ((b.twist ?? 0) - (a.twist ?? 0)) * t,
  };
}

// ── Trace builders ───────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PlotlyData = any;

const COLOR_AIRFOIL = "#FF8400";     // all airfoils: orange, thick
const COLOR_INTERP = "#FF8400";      // interpolated: same orange
const COLOR_CAMBER = "#7A7B78";
const COLOR_QC = "#30A46C";
const COLOR_SPANWISE = "#FF840060";
const COLOR_SELECTED = "#E5484D";    // selected xsec/segment: red
const COLOR_TED = "#30A46C";
const COLOR_SPAR = "#6E56CF";        // purple

/** Shorthand for a scatter3d trace. */
function scatter3d(
  x: number[], y: number[], z: number[],
  color: string, width: number, dash?: string,
): PlotlyData {
  return {
    type: "scatter3d",
    mode: "lines",
    x, y, z,
    line: { color, width, ...(dash ? { dash } : {}) },
    showlegend: false,
    hoverinfo: "skip",
  };
}

// ── Wing trace context shared across sub-builders ────────────────

interface WingTraceCtx {
  xsecs: XSec[];
  airfoils: (AirfoilCoords | null)[];
  dihedrals: number[];
  selectedIdx: number | null;
}

/** Compute dihedral angle at each station from span direction (YZ plane). */
function computeDihedrals(xsecs: XSec[]): number[] {
  const dihedrals: number[] = [];
  for (let i = 0; i < xsecs.length; i++) {
    let dy: number, dz: number;
    if (i < xsecs.length - 1) {
      dy = xsecs[i + 1].xyz_le[1] - xsecs[i].xyz_le[1];
      dz = xsecs[i + 1].xyz_le[2] - xsecs[i].xyz_le[2];
    } else {
      dy = xsecs[i].xyz_le[1] - xsecs[i - 1].xyz_le[1];
      dz = xsecs[i].xyz_le[2] - xsecs[i - 1].xyz_le[2];
    }
    dihedrals.push(Math.atan2(dz, dy));
  }
  return dihedrals;
}

/** Per-station airfoil contour + camber line traces. */
function buildStationAirfoilTraces(ctx: WingTraceCtx): PlotlyData[] {
  const traces: PlotlyData[] = [];
  const { xsecs, airfoils, dihedrals, selectedIdx } = ctx;

  for (let i = 0; i < xsecs.length; i++) {
    const xs = xsecs[i];
    const af = airfoils[i];
    const isSelected = selectedIdx === i;
    const color = isSelected ? COLOR_SELECTED : COLOR_AIRFOIL;
    const width = isSelected ? 3.5 : 2;
    const dih = dihedrals[i];

    if (af) {
      const p = transformProfile(af.x, af.y, xs.chord, xs.twist, xs.xyz_le, dih);
      traces.push(scatter3d(p.x, p.y, p.z, color, width));

      const c = transformProfile(af.camber_x, af.camber_y, xs.chord, xs.twist, xs.xyz_le, dih);
      traces.push(scatter3d(c.x, c.y, c.z, isSelected ? COLOR_SELECTED : COLOR_CAMBER, 1, "dot"));
    }
  }

  return traces;
}

/** Interpolated airfoil profiles between adjacent stations. */
function buildInterpolatedAirfoilTraces(ctx: WingTraceCtx): PlotlyData[] {
  const traces: PlotlyData[] = [];
  const { xsecs, airfoils, dihedrals, selectedIdx } = ctx;
  const nInterp = 3;

  for (let i = 0; i < xsecs.length - 1; i++) {
    const afA = airfoils[i];
    const afB = airfoils[i + 1];
    if (!afA || !afB) continue;

    const segSelected = selectedIdx === i;

    for (let k = 1; k <= nInterp; k++) {
      const t = k / (nInterp + 1);
      const station = lerpStation(xsecs[i], xsecs[i + 1], t);
      const interpDih = dihedrals[i] + (dihedrals[i + 1] - dihedrals[i]) * t;
      const profile = lerpProfile(afA, afB, t);
      const p = transformProfile(profile.x, profile.y, station.chord, station.twist, station.xyz_le, interpDih);
      traces.push(scatter3d(p.x, p.y, p.z, segSelected ? COLOR_SELECTED : COLOR_INTERP, segSelected ? 1.5 : 1));
    }
  }

  return traces;
}

/** Spanwise quarter-chord, upper, and lower reference lines. */
function buildQuarterChordTraces(ctx: WingTraceCtx): PlotlyData[] {
  const traces: PlotlyData[] = [];
  const { xsecs, airfoils, dihedrals } = ctx;

  const qcX: number[] = [], qcY: number[] = [], qcZ: number[] = [];
  const upperQcX: number[] = [], upperQcY: number[] = [], upperQcZ: number[] = [];
  const lowerQcX: number[] = [], lowerQcY: number[] = [], lowerQcZ: number[] = [];

  for (let i = 0; i < xsecs.length; i++) {
    const xs = xsecs[i];
    const af = airfoils[i];
    const qcFrac = 0.25;

    if (af) {
      const camberY = lerpLookup(af.camber_x, af.camber_y, qcFrac);
      const qc = transformProfile([qcFrac], [camberY], xs.chord, xs.twist, xs.xyz_le, dihedrals[i]);
      qcX.push(qc.x[0]); qcY.push(qc.y[0]); qcZ.push(qc.z[0]);

      const upperY = lerpLookup(af.upper_x, af.upper_y, qcFrac);
      const up = transformProfile([qcFrac], [upperY], xs.chord, xs.twist, xs.xyz_le, dihedrals[i]);
      upperQcX.push(up.x[0]); upperQcY.push(up.y[0]); upperQcZ.push(up.z[0]);

      const lowerY = lerpLookup(af.lower_x, af.lower_y, qcFrac);
      const lo = transformProfile([qcFrac], [lowerY], xs.chord, xs.twist, xs.xyz_le, dihedrals[i]);
      lowerQcX.push(lo.x[0]); lowerQcY.push(lo.y[0]); lowerQcZ.push(lo.z[0]);
    } else {
      const qcPt = transformProfile([qcFrac], [0], xs.chord, xs.twist, xs.xyz_le, dihedrals[i]);
      qcX.push(qcPt.x[0]); qcY.push(qcPt.y[0]); qcZ.push(qcPt.z[0]);
      upperQcX.push(qcPt.x[0]); upperQcY.push(qcPt.y[0]); upperQcZ.push(qcPt.z[0]);
      lowerQcX.push(qcPt.x[0]); lowerQcY.push(qcPt.y[0]); lowerQcZ.push(qcPt.z[0]);
    }
  }

  traces.push(scatter3d(qcX, qcY, qcZ, COLOR_QC, 2.5));
  traces.push(scatter3d(upperQcX, upperQcY, upperQcZ, COLOR_SPANWISE, 1.5));
  traces.push(scatter3d(lowerQcX, lowerQcY, lowerQcZ, COLOR_SPANWISE, 1.5));

  return traces;
}

/** Leading and trailing edge lines per segment. */
function buildEdgeTraces(ctx: WingTraceCtx): PlotlyData[] {
  const traces: PlotlyData[] = [];
  const { xsecs, dihedrals, selectedIdx } = ctx;

  for (let i = 0; i < xsecs.length - 1; i++) {
    const segSelected = selectedIdx === i;
    const color = segSelected ? COLOR_SELECTED : COLOR_AIRFOIL;
    const width = segSelected ? 3 : 2;

    // LE segment
    traces.push(scatter3d(
      [xsecs[i].xyz_le[0], xsecs[i + 1].xyz_le[0]],
      [xsecs[i].xyz_le[1], xsecs[i + 1].xyz_le[1]],
      [xsecs[i].xyz_le[2], xsecs[i + 1].xyz_le[2]],
      color, width,
    ));

    // TE segment
    const te1 = transformProfile([1], [0], xsecs[i].chord, xsecs[i].twist, xsecs[i].xyz_le, dihedrals[i]);
    const te2 = transformProfile([1], [0], xsecs[i + 1].chord, xsecs[i + 1].twist, xsecs[i + 1].xyz_le, dihedrals[i + 1]);
    traces.push(scatter3d(
      [te1.x[0], te2.x[0]],
      [te1.y[0], te2.y[0]],
      [te1.z[0], te2.z[0]],
      color, width,
    ));
  }

  return traces;
}

/** Trailing edge device (TED) outlines. */
function buildTEDTraces(ctx: WingTraceCtx): PlotlyData[] {
  const traces: PlotlyData[] = [];
  const { xsecs, dihedrals } = ctx;

  for (let i = 0; i < xsecs.length; i++) {
    const ted = xsecs[i].trailing_edge_device ?? xsecs[i].control_surface;
    if (!ted) continue;
    const relChord = (ted as Record<string, unknown>).rel_chord_root as number | undefined;
    if (relChord == null) continue;

    const nextI = Math.min(i + 1, xsecs.length - 1);
    const nextTed = xsecs[nextI]?.trailing_edge_device ?? xsecs[nextI]?.control_surface;
    const nextRelChord = nextTed
      ? ((nextTed as Record<string, unknown>).rel_chord_tip as number ?? relChord)
      : relChord;

    const h1 = transformProfile([relChord], [0], xsecs[i].chord, xsecs[i].twist, xsecs[i].xyz_le, dihedrals[i]);
    const h2 = transformProfile([nextRelChord], [0], xsecs[nextI].chord, xsecs[nextI].twist, xsecs[nextI].xyz_le, dihedrals[nextI]);
    const te1 = transformProfile([1], [0], xsecs[i].chord, xsecs[i].twist, xsecs[i].xyz_le, dihedrals[i]);
    const te2 = transformProfile([1], [0], xsecs[nextI].chord, xsecs[nextI].twist, xsecs[nextI].xyz_le, dihedrals[nextI]);

    // Hinge line
    traces.push(scatter3d([h1.x[0], h2.x[0]], [h1.y[0], h2.y[0]], [h1.z[0], h2.z[0]], COLOR_TED, 3));
    // TED area outline
    traces.push(scatter3d(
      [h1.x[0], te1.x[0], te2.x[0], h2.x[0], h1.x[0]],
      [h1.y[0], te1.y[0], te2.y[0], h2.y[0], h1.y[0]],
      [h1.z[0], te1.z[0], te2.z[0], h2.z[0], h1.z[0]],
      COLOR_TED, 1.5,
    ));
  }

  return traces;
}

// ── Spar helpers ─────────────────────────────────────────────────

const N_CIRCLE_PTS = 16;

/** Draw a spar cross-section (circle or rectangle) at a 3D center point. */
function buildSparCrossSection(
  center: { x: number[]; y: number[]; z: number[] },
  sparW: number, sparH: number, twist: number, color: string,
): PlotlyData | null {
  if (sparW <= 0 || sparH <= 0) return null;
  const cx: number[] = [], cy: number[] = [], cz: number[] = [];
  const isCircle = Math.abs(sparW - sparH) < 0.0001;
  if (isCircle) {
    const r = sparW / 2;
    for (let j = 0; j <= N_CIRCLE_PTS; j++) {
      const theta = (2 * Math.PI * j) / N_CIRCLE_PTS;
      cx.push(center.x[0] + r * Math.cos(theta) * Math.cos(twist * Math.PI / 180));
      cy.push(center.y[0]);
      cz.push(center.z[0] + r * Math.sin(theta));
    }
  } else {
    const hw = sparW / 2, hh = sparH / 2;
    const twistRad = (twist ?? 0) * Math.PI / 180;
    const cosT = Math.cos(twistRad);
    const corners = [[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh], [-hw, -hh]];
    for (const [dx, dz] of corners) {
      cx.push(center.x[0] + dx * cosT);
      cy.push(center.y[0]);
      cz.push(center.z[0] + dz);
    }
  }
  return scatter3d(cx, cy, cz, color, 1.5);
}

/** Interpolate xsec properties at spanwise fraction t (0=root, 1=tip). */
function lerpXSec(
  xsecs: XSec[], dihedrals: number[],
  rootIdx: number, tipIdx: number, t: number,
): { chord: number; twist: number; xyz_le: number[]; dihedral: number } {
  const r = xsecs[rootIdx], tip = xsecs[tipIdx];
  return {
    chord: r.chord * (1 - t) + tip.chord * t,
    twist: r.twist * (1 - t) + tip.twist * t,
    xyz_le: r.xyz_le.map((v, k) => v * (1 - t) + tip.xyz_le[k] * t),
    dihedral: dihedrals[rootIdx] * (1 - t) + dihedrals[tipIdx] * t,
  };
}

/** Interpolate airfoil coordinates at spanwise fraction t. */
function lerpAf(
  airfoils: (AirfoilCoords | null)[],
  rootIdx: number, tipIdx: number, t: number,
): AirfoilCoords | null {
  const afA = airfoils[rootIdx], afB = airfoils[tipIdx];
  if (!afA && !afB) return null;
  if (!afA) return afB;
  if (!afB) return afA;
  const nPts = 60;
  const interpSurface = (
    axArr: number[], ayArr: number[], bxArr: number[], byArr: number[],
  ) => {
    const xs: number[] = [], ys: number[] = [];
    for (let j = 0; j <= nPts; j++) {
      const xNorm = j / nPts;
      xs.push(xNorm);
      ys.push(lerpLookup(axArr, ayArr, xNorm) * (1 - t) + lerpLookup(bxArr, byArr, xNorm) * t);
    }
    return { x: xs, y: ys };
  };
  const upper = interpSurface(afA.upper_x, afA.upper_y, afB.upper_x, afB.upper_y);
  const lower = interpSurface(afA.lower_x, afA.lower_y, afB.lower_x, afB.lower_y);
  const camber = interpSurface(afA.camber_x, afA.camber_y, afB.camber_x, afB.camber_y);
  return {
    x: upper.x, y: upper.y,
    upper_x: upper.x, upper_y: upper.y,
    lower_x: lower.x, lower_y: lower.y,
    camber_x: camber.x, camber_y: camber.y,
  };
}

/** Build vertical spar line at a station (upper to lower surface). */
function buildSparVerticalLine(
  af: AirfoilCoords | null, posFactor: number,
  station: { chord: number; twist: number; xyz_le: number[]; dihedral: number },
  color: string,
): PlotlyData {
  if (af) {
    const upperY = lerpLookup(af.upper_x, af.upper_y, posFactor);
    const lowerY = lerpLookup(af.lower_x, af.lower_y, posFactor);
    const top = transformProfile([posFactor], [upperY], station.chord, station.twist, station.xyz_le, station.dihedral);
    const bot = transformProfile([posFactor], [lowerY], station.chord, station.twist, station.xyz_le, station.dihedral);
    return scatter3d(
      [top.x[0], bot.x[0]], [top.y[0], bot.y[0]], [top.z[0], bot.z[0]],
      color, 2,
    );
  }
  const ptUp = transformProfile([posFactor], [0.05], station.chord, station.twist, station.xyz_le, station.dihedral);
  const ptDn = transformProfile([posFactor], [-0.05], station.chord, station.twist, station.xyz_le, station.dihedral);
  return scatter3d(
    [ptUp.x[0], ptDn.x[0]], [ptUp.y[0], ptDn.y[0]], [ptUp.z[0], ptDn.z[0]],
    color, 2,
  );
}

/** Build spanwise connection lines (upper + lower surface) for a spar. */
function buildSparSpanwiseLines(
  startAf: AirfoilCoords, endAf: AirfoilCoords, posFactor: number,
  startStation: { chord: number; twist: number; xyz_le: number[]; dihedral: number },
  endStation: { chord: number; twist: number; xyz_le: number[]; dihedral: number },
  color: string,
): PlotlyData[] {
  const traces: PlotlyData[] = [];

  const upperY1 = lerpLookup(startAf.upper_x, startAf.upper_y, posFactor);
  const upperY2 = lerpLookup(endAf.upper_x, endAf.upper_y, posFactor);
  const up1 = transformProfile([posFactor], [upperY1], startStation.chord, startStation.twist, startStation.xyz_le, startStation.dihedral);
  const up2 = transformProfile([posFactor], [upperY2], endStation.chord, endStation.twist, endStation.xyz_le, endStation.dihedral);
  traces.push(scatter3d(
    [up1.x[0], up2.x[0]], [up1.y[0], up2.y[0]], [up1.z[0], up2.z[0]],
    color, 1.5,
  ));

  const lowerY1 = lerpLookup(startAf.lower_x, startAf.lower_y, posFactor);
  const lowerY2 = lerpLookup(endAf.lower_x, endAf.lower_y, posFactor);
  const lo1 = transformProfile([posFactor], [lowerY1], startStation.chord, startStation.twist, startStation.xyz_le, startStation.dihedral);
  const lo2 = transformProfile([posFactor], [lowerY2], endStation.chord, endStation.twist, endStation.xyz_le, endStation.dihedral);
  traces.push(scatter3d(
    [lo1.x[0], lo2.x[0]], [lo1.y[0], lo2.y[0]], [lo1.z[0], lo2.z[0]],
    color, 1.5,
  ));

  return traces;
}

/** Build dashed edge lines along spar corners/extremes. */
function buildSparEdgeLines(
  startCenter: { x: number[]; y: number[]; z: number[] },
  endCenter: { x: number[]; y: number[]; z: number[] },
  sparW: number, sparH: number,
  startTwist: number, endTwist: number,
  color: string,
): PlotlyData[] {
  const traces: PlotlyData[] = [];
  const isCircle = Math.abs(sparW - sparH) < 0.0001;
  const edgeOffsets: [number, number][] = isCircle
    ? [[0, sparW / 2], [0, -sparW / 2], [sparW / 2, 0], [-sparW / 2, 0]]
    : [[sparW / 2, sparH / 2], [-sparW / 2, sparH / 2], [-sparW / 2, -sparH / 2], [sparW / 2, -sparH / 2]];

  for (const [dChord, dVert] of edgeOffsets) {
    const tw1 = (startTwist ?? 0) * Math.PI / 180;
    const tw2 = (endTwist ?? 0) * Math.PI / 180;
    const e1x = startCenter.x[0] + dChord * Math.cos(tw1);
    const e1y = startCenter.y[0];
    const e1z = startCenter.z[0] + dVert;
    const e2x = endCenter.x[0] + dChord * Math.cos(tw2);
    const e2y = endCenter.y[0];
    const e2z = endCenter.z[0] + dVert;
    traces.push(scatter3d(
      [e1x, e2x], [e1y, e2y], [e1z, e2z],
      color, 1, "dash",
    ));
  }

  return traces;
}

/** All spar traces for the wing. */
function buildSparTraces(ctx: WingTraceCtx): PlotlyData[] {
  const traces: PlotlyData[] = [];
  const { xsecs, airfoils, dihedrals, selectedIdx } = ctx;

  for (let i = 0; i < xsecs.length; i++) {
    const spars = xsecs[i].spare_list as Array<Record<string, unknown>> | undefined;
    if (!spars || spars.length === 0) continue;
    if (i >= xsecs.length - 1) continue;
    const sparColor = selectedIdx === i ? COLOR_SELECTED : COLOR_SPAR;

    const dx = xsecs[i + 1].xyz_le[0] - xsecs[i].xyz_le[0];
    const dy = xsecs[i + 1].xyz_le[1] - xsecs[i].xyz_le[1];
    const dz = xsecs[i + 1].xyz_le[2] - xsecs[i].xyz_le[2];
    const segmentSpan = Math.sqrt(dx * dx + dy * dy + dz * dz);

    for (const spar of spars) {
      const posFactor = spar.spare_position_factor as number | undefined;
      if (posFactor == null) continue;
      const sparW = (spar.spare_support_dimension_width as number ?? 0) * 0.001;
      const sparH = (spar.spare_support_dimension_height as number ?? 0) * 0.001;
      const sparStartMm = spar.spare_start as number ?? 0;
      const sparLengthMm = spar.spare_length as number | undefined;

      const tStart = segmentSpan > 0 ? (sparStartMm * 0.001) / segmentSpan : 0;
      const tEnd = (sparLengthMm != null && segmentSpan > 0)
        ? Math.min((sparStartMm + sparLengthMm) * 0.001 / segmentSpan, 1)
        : 1;

      const startStation = lerpXSec(xsecs, dihedrals, i, i + 1, tStart);
      const startAf = lerpAf(airfoils, i, i + 1, tStart);
      const endStation = lerpXSec(xsecs, dihedrals, i, i + 1, tEnd);
      const endAf = lerpAf(airfoils, i, i + 1, tEnd);

      // Compute spar center points
      const sparOrigin = spar.spare_origin as number[] | null | undefined;
      const sparVector = spar.spare_vector as number[] | null | undefined;
      const hasPrecise = sparOrigin && sparVector && sparOrigin.length === 3 && sparVector.length === 3;

      let startCenter: { x: number[]; y: number[]; z: number[] } | null = null;
      let endCenter: { x: number[]; y: number[]; z: number[] } | null = null;

      if (hasPrecise) {
        const startDist = sparStartMm * 0.001;
        const endDist = (sparLengthMm != null ? (sparStartMm + sparLengthMm) * 0.001 : segmentSpan);
        startCenter = {
          x: [sparOrigin[0] + sparVector[0] * startDist],
          y: [sparOrigin[1] + sparVector[1] * startDist],
          z: [sparOrigin[2] + sparVector[2] * startDist],
        };
        endCenter = {
          x: [sparOrigin[0] + sparVector[0] * endDist],
          y: [sparOrigin[1] + sparVector[1] * endDist],
          z: [sparOrigin[2] + sparVector[2] * endDist],
        };
      } else {
        if (startAf) {
          const camberY = lerpLookup(startAf.camber_x, startAf.camber_y, posFactor);
          startCenter = transformProfile([posFactor], [camberY], startStation.chord, startStation.twist, startStation.xyz_le, startStation.dihedral);
        }
        if (endAf) {
          const camberY = lerpLookup(endAf.camber_x, endAf.camber_y, posFactor);
          endCenter = transformProfile([posFactor], [camberY], endStation.chord, endStation.twist, endStation.xyz_le, endStation.dihedral);
        }
      }

      // Vertical spar lines + cross-sections
      traces.push(buildSparVerticalLine(startAf, posFactor, startStation, sparColor));
      if (startCenter) {
        const cs = buildSparCrossSection(startCenter, sparW, sparH, startStation.twist, sparColor);
        if (cs) traces.push(cs);
      }

      traces.push(buildSparVerticalLine(endAf, posFactor, endStation, sparColor));
      if (endCenter) {
        const cs = buildSparCrossSection(endCenter, sparW, sparH, endStation.twist, sparColor);
        if (cs) traces.push(cs);
      }

      // Spanwise connection lines
      if (startAf && endAf) {
        traces.push(...buildSparSpanwiseLines(startAf, endAf, posFactor, startStation, endStation, sparColor));
      }

      // Dashed edge lines
      if (startCenter && endCenter && sparW > 0 && sparH > 0) {
        traces.push(...buildSparEdgeLines(startCenter, endCenter, sparW, sparH, startStation.twist, endStation.twist, sparColor));
      }
    }
  }

  return traces;
}

/** Apply mirror for symmetric wings. */
function mirrorTraces(traces: PlotlyData[]): PlotlyData[] {
  return traces.map((t) => ({
    ...t,
    y: (t.y as number[]).map((v: number) => -v),
  }));
}

// ── Main wing trace builder ─────────────────────────────────────

async function buildAllWingTraces(
  wing: Wing,
  selectedIdx: number | null,
  showQC = false,
): Promise<PlotlyData[]> {
  const xsecs = wing.x_secs;
  if (xsecs.length < 2) return [];

  // Fetch all airfoil coordinates
  const airfoils: (AirfoilCoords | null)[] = [];
  for (const xs of xsecs) {
    airfoils.push(await fetchAirfoilCoords(xs.airfoil));
  }

  const dihedrals = computeDihedrals(xsecs);
  const ctx: WingTraceCtx = { xsecs, airfoils, dihedrals, selectedIdx };

  const traces: PlotlyData[] = [
    ...buildStationAirfoilTraces(ctx),
    ...buildInterpolatedAirfoilTraces(ctx),
    ...(showQC ? buildQuarterChordTraces(ctx) : []),
    ...buildEdgeTraces(ctx),
    ...buildTEDTraces(ctx),
    ...buildSparTraces(ctx),
  ];

  if (wing.symmetric) {
    traces.push(...mirrorTraces(traces));
  }

  return traces;
}

/** Build superellipse cross-section traces for a fuselage. */
const COLOR_FUSELAGE_HIGHLIGHT = "#FACC15"; // yellow for selected fuselage xsec

function buildFuselageTraces(fuselage: Fuselage, color: string, selectedIdx: number | null = null) {
  const traces: PlotlyData[] = [];
  const xsecs = fuselage.x_secs;
  if (xsecs.length < 2) return traces;

  // Centerline (dashed)
  traces.push(scatter3d(
    xsecs.map((xs) => xs.xyz[0]),
    xsecs.map((xs) => xs.xyz[1]),
    xsecs.map((xs) => xs.xyz[2]),
    color, 1.5, "dash",
  ));

  // Cross-section outlines
  const nPts = 32;
  for (let idx = 0; idx < xsecs.length; idx++) {
    const xs = xsecs[idx];
    const isSelected = selectedIdx === idx;
    const xsecColor = isSelected ? COLOR_FUSELAGE_HIGHLIGHT : color;
    const xsecWidth = isSelected ? 3 : 1.5;
    const cx: number[] = [], cy: number[] = [], cz: number[] = [];
    for (let j = 0; j <= nPts; j++) {
      const theta = (2 * Math.PI * j) / nPts;
      const cosT = Math.cos(theta);
      const sinT = Math.sin(theta);
      const r_y = xs.a * Math.sign(cosT) * Math.pow(Math.abs(cosT), 2 / xs.n);
      const r_z = xs.b * Math.sign(sinT) * Math.pow(Math.abs(sinT), 2 / xs.n);
      cx.push(xs.xyz[0]);
      cy.push(xs.xyz[1] + r_y);
      cz.push(xs.xyz[2] + r_z);
    }
    traces.push(scatter3d(cx, cy, cz, xsecColor, xsecWidth));
  }

  // Longitudinal lines (solid, along top/bottom/sides)
  for (const angle of [0, Math.PI / 2, Math.PI, 3 * Math.PI / 2]) {
    const lx: number[] = [], ly: number[] = [], lz: number[] = [];
    for (const xs of xsecs) {
      const cosT = Math.cos(angle);
      const sinT = Math.sin(angle);
      const r_y = xs.a * Math.sign(cosT) * Math.pow(Math.abs(cosT + 1e-10), 2 / xs.n);
      const r_z = xs.b * Math.sign(sinT) * Math.pow(Math.abs(sinT + 1e-10), 2 / xs.n);
      lx.push(xs.xyz[0]);
      ly.push(xs.xyz[1] + r_y);
      lz.push(xs.xyz[2] + r_z);
    }
    traces.push(scatter3d(lx, ly, lz, color, 1.5));
  }

  return traces;
}

// ── Plotly layout configuration ─────────────────────────────────

function buildPlotlyLayout() {
  return {
    paper_bgcolor: "#17171A",
    plot_bgcolor: "#17171A",
    scene: {
      xaxis: { showgrid: true, gridcolor: "#2E2E2E", zerolinecolor: "#3A3A3A", color: "#7A7B78", title: "x" },
      yaxis: { showgrid: true, gridcolor: "#2E2E2E", zerolinecolor: "#3A3A3A", color: "#7A7B78", title: "y" },
      zaxis: { showgrid: true, gridcolor: "#2E2E2E", zerolinecolor: "#3A3A3A", color: "#7A7B78", title: "z" },
      aspectmode: "data",
      bgcolor: "#17171A",
    },
    margin: { l: 0, r: 0, t: 32, b: 0 },
    showlegend: false,
    updatemenus: [{
      type: "buttons",
      direction: "left",
      x: 1.0,
      y: 1.05,
      xanchor: "right",
      yanchor: "bottom",
      bgcolor: "#1A1A1A",
      bordercolor: "#2E2E2E",
      borderwidth: 1,
      font: { color: "#B8B9B6", size: 10, family: "JetBrains Mono, monospace" },
      buttons: [
        {
          label: "Top",
          method: "relayout",
          args: [{ "scene.camera": { eye: { x: 0, y: 0, z: 2 }, up: { x: -1, y: 0, z: 0 } } }],
        },
        {
          label: "Front",
          method: "relayout",
          args: [{ "scene.camera": { eye: { x: -2, y: 0, z: 0 }, up: { x: 0, y: 0, z: 1 } } }],
        },
        {
          label: "Side",
          method: "relayout",
          args: [{ "scene.camera": { eye: { x: 0, y: -2, z: 0 }, up: { x: 0, y: 0, z: 1 } } }],
        },
      ],
    }, {
      type: "buttons",
      direction: "left",
      x: 0.0,
      y: 1.05,
      xanchor: "left",
      yanchor: "bottom",
      bgcolor: "#1A1A1A",
      bordercolor: "#2E2E2E",
      borderwidth: 1,
      font: { color: "#B8B9B6", size: 10, family: "JetBrains Mono, monospace" },
      buttons: [
        {
          label: "Perspective",
          method: "relayout",
          args: [{ "scene.camera.projection": { type: "perspective" } }],
        },
        {
          label: "Ortho",
          method: "relayout",
          args: [{ "scene.camera.projection": { type: "orthographic" } }],
        },
      ],
    }],
  };
}

/** Collect all traces from visible wings and fuselages. */
async function collectAllTraces(
  wings: Wing[], fuselages: Fuselage[],
  visibleWings: Set<string>, visibleFuselages: Set<string>,
  selectedWing: string | null, selectedXsecIndex: number | null,
  selectedFuselage: string | null, selectedFuselageXsecIndex: number | null,
  showQuarterChord: boolean,
): Promise<PlotlyData[]> {
  const traces: PlotlyData[] = [];

  for (const wing of wings) {
    if (!visibleWings.has(wing.name)) continue;
    const selIdx = selectedWing === wing.name ? selectedXsecIndex : null;
    const wingTraces = await buildAllWingTraces(wing, selIdx, showQuarterChord);
    traces.push(...wingTraces);
  }

  for (const fuse of fuselages) {
    if (!visibleFuselages.has(fuse.name)) continue;
    const fuseSelIdx = selectedFuselage === fuse.name ? selectedFuselageXsecIndex : null;
    traces.push(...buildFuselageTraces(fuse, "#3B82F6", fuseSelIdx));
  }

  return traces;
}

// ── Component ────────────────────────────────────────────────────

export function WingOutlineViewer({
  wings, fuselages, visibleWings, visibleFuselages,
  selectedXsecIndex = null, selectedWing = null,
  selectedFuselage = null, selectedFuselageXsecIndex = null,
}: WingOutlineViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const plotlyRef = useRef<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const savedCamera = useRef<any>(null);
  const [loading, setLoading] = useState(true);
  const [showQuarterChord, setShowQuarterChord] = useState(false);

  useEffect(() => {
    let disposed = false;

    async function render() {
      if (!containerRef.current) return;
      setLoading(true);

      const Plotly = await import("plotly.js-gl3d-dist-min");
      if (disposed) return;
      plotlyRef.current = Plotly;

      const traces = await collectAllTraces(
        wings, fuselages, visibleWings, visibleFuselages,
        selectedWing ?? null, selectedXsecIndex ?? null,
        selectedFuselage ?? null, selectedFuselageXsecIndex ?? null,
        showQuarterChord,
      );

      // Guard: empty scene placeholder to avoid Plotly GL crashes
      if (traces.length === 0) {
        traces.push({
          type: "scatter3d", mode: "lines",
          x: [0], y: [0], z: [0],
          line: { color: "transparent", width: 0 },
          showlegend: false, hoverinfo: "skip",
        } as PlotlyData);
      }

      const layout = buildPlotlyLayout();
      const config = { displayModeBar: false, responsive: true };

      // Save camera before replot
      const el = containerRef.current as unknown as { layout?: { scene?: { camera?: unknown } } } | null;
      const currentCamera = el?.layout?.scene?.camera;
      if (currentCamera) savedCamera.current = currentCamera;

      await Plotly.newPlot(containerRef.current, traces, layout, config);

      // Restore saved camera
      if (savedCamera.current) {
        try { Plotly.relayout(containerRef.current, { "scene.camera": savedCamera.current }); } catch { /* ok */ }
      }

      // Track camera changes from user interaction
      containerRef.current?.on?.("plotly_relayout", (update: Record<string, unknown>) => {
        if (update["scene.camera"]) savedCamera.current = update["scene.camera"];
      });

      setLoading(false);
    }

    render();

    return () => {
      disposed = true;
      if (containerRef.current && plotlyRef.current) {
        try { plotlyRef.current.purge(containerRef.current); } catch { /* ok */ }
      }
    };
  }, [wings, fuselages, visibleWings, visibleFuselages, selectedXsecIndex, selectedWing, selectedFuselage, selectedFuselageXsecIndex, showQuarterChord]);

  return (
    <div className="relative h-full w-full">
      {loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-card-muted/80">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
            Loading preview…
          </span>
        </div>
      )}
      {/* Toggle buttons */}
      <div className="absolute bottom-3 right-3 z-20 flex gap-1">
        <button
          onClick={() => setShowQuarterChord((v) => !v)}
          className={`rounded-lg border px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[10px] backdrop-blur-sm ${
            showQuarterChord
              ? "border-primary bg-primary/20 text-primary"
              : "border-border bg-card/80 text-muted-foreground hover:text-foreground"
          }`}
        >
          ¼ Chord
        </button>
      </div>
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
}
