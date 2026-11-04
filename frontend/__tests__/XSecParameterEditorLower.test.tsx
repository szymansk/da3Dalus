/**
 * Import dialog: the lower-half exponent of a sliced section is editable
 * (gh-1157). Empty means "same as n".
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React, { useEffect, useState } from "react";

vi.mock("@/lib/fetcher", () => ({ API_BASE: "http://api.test" }));

import { XSecParameterEditor, type XSec } from "@/components/workbench/ImportFuselageDialog";

let latest: XSec[] = [];

function Harness({ initial }: Readonly<{ initial: XSec[] }>) {
  const [xsecs, setXsecs] = useState(initial);
  useEffect(() => {
    latest = xsecs;
  }, [xsecs]);
  return <XSecParameterEditor xsecs={xsecs} selectedXsec={1} setXsecs={setXsecs} />;
}

const SECTIONS: XSec[] = [
  { xyz: [0, 0, 0], a: 0.05, b: 0.04, n: 2 },
  { xyz: [0.1, 0, 0], a: 0.06, b: 0.05, n: 2.5 },
];

describe("XSecParameterEditor n_lower field", () => {
  it("sets, clamps and clears n_lower on the selected section only", () => {
    render(<Harness initial={SECTIONS} />);
    const field = screen.getByLabelText("n lower (bottom, empty = n)") as HTMLInputElement;
    expect(field.value).toBe("");

    fireEvent.change(field, { target: { value: "8" } });
    expect(latest[1].n_lower).toBe(8);
    expect(latest[0].n_lower).toBeUndefined();

    fireEvent.change(field, { target: { value: "99" } });
    expect(latest[1].n_lower).toBe(50);

    fireEvent.change(field, { target: { value: "" } });
    expect(latest[1].n_lower).toBeNull();
  });

  it("still edits the position vector component-wise", () => {
    render(<Harness initial={SECTIONS} />);
    fireEvent.change(screen.getByLabelText("xyz[z]"), { target: { value: "0.02" } });
    expect(latest[1].xyz).toEqual([0.1, 0, 0.02]);
  });
});

describe("XSecParameterEditor on a section with a contour (gh-1349)", () => {
  const CONTOUR: [number, number][] = [
    [0, -0.05], [0.03, -0.04], [0.05, -0.02], [0.06, 0], [0.05, 0.02], [0.03, 0.04],
    [0.01, 0.049], [0, 0.05],
  ];

  it("warns that the contour wins and keeps the contour when the fit is edited", () => {
    render(<Harness initial={[SECTIONS[0], { ...SECTIONS[1], contour: CONTOUR }]} />);
    expect(screen.getByText(/contour \(8 points\)\. The contour wins/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("a (width/2)"), { target: { value: "0.07" } });
    expect(latest[1].a).toBe(0.07);
    expect(latest[1].contour).toEqual(CONTOUR);
  });

  it("shows no warning for a plain section", () => {
    render(<Harness initial={SECTIONS} />);
    expect(screen.queryByText(/The contour wins/)).toBeNull();
  });
});
