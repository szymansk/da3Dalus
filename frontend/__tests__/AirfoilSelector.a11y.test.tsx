/**
 * A11y tests for AirfoilSelector — ITEM 6.
 * Asserts that root and tip AirfoilSelector instances get UNIQUE, non-empty
 * ids so there are no duplicate-id violations.
 *
 * Background: AirfoilPreviewConfigPanel previously passed label='' to both
 * selectors, causing BOTH to derive id='airfoil-' (duplicate empty id).
 * Fix: additive optional `id` prop on AirfoilSelector; ConfigPanel passes
 * id='airfoil-root' and id='airfoil-tip'.
 */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import React from "react";

// Mock SWR for the airfoil list used by AirfoilSelector
vi.mock("swr", () => ({
  default: vi.fn(() => ({
    data: {
      count: 2,
      airfoils: [
        { airfoil_name: "naca0015", file_name: "naca0015.dat" },
        { airfoil_name: "e423", file_name: "e423.dat" },
      ],
    },
    error: null,
    isLoading: false,
  })),
}));

vi.mock("lucide-react", () => ({
  ChevronDown: (p: Record<string, unknown>) => <svg data-testid="chevron-down" {...p} />,
  ChevronUp: (p: Record<string, unknown>) => <svg data-testid="chevron-up" {...p} />,
  Search: (p: Record<string, unknown>) => <svg data-testid="search" {...p} />,
  Check: (p: Record<string, unknown>) => <svg data-testid="check" {...p} />,
  Info: (p: Record<string, unknown>) => <svg data-testid="info" {...p} />,
  ArrowLeft: (p: Record<string, unknown>) => <svg data-testid="arrow-left" {...p} />,
  Save: (p: Record<string, unknown>) => <svg data-testid="save" {...p} />,
  Loader2: (p: Record<string, unknown>) => <svg data-testid="loader2" {...p} />,
  ChevronLeft: (p: Record<string, unknown>) => <svg data-testid="chevron-left" {...p} />,
  ChevronRight: (p: Record<string, unknown>) => <svg data-testid="chevron-right" {...p} />,
  Undo2: (p: Record<string, unknown>) => <svg data-testid="undo2" {...p} />,
  AlertTriangle: (p: Record<string, unknown>) => <svg data-testid="alert-triangle" {...p} />,
}));

import { AirfoilSelector } from "../components/workbench/AirfoilSelector";
import { AirfoilPreviewConfigPanel } from "../components/workbench/AirfoilPreviewConfigPanel";

// ── Standalone AirfoilSelector id prop ────────────────────────────

describe("AirfoilSelector — additive id prop (ITEM 6)", () => {
  it("uses the provided id on the trigger button when id prop is given", () => {
    const { container } = render(
      <AirfoilSelector label="" value="naca0015" id="airfoil-root" />,
    );
    const trigger = container.querySelector("#airfoil-root");
    expect(trigger).not.toBeNull();
    expect(trigger?.tagName.toLowerCase()).toBe("button");
  });

  it("uses the provided id on the label htmlFor when id prop is given", () => {
    const { container } = render(
      <AirfoilSelector label="" value="naca0015" id="airfoil-root" />,
    );
    const label = container.querySelector('label[for="airfoil-root"]');
    expect(label).not.toBeNull();
  });

  it("falls back to label-derived id when id prop is absent", () => {
    const { container } = render(
      <AirfoilSelector label="Root" value="naca0015" />,
    );
    const trigger = container.querySelector("#airfoil-root");
    expect(trigger).not.toBeNull();
  });

  it("two selectors with different id props have UNIQUE ids", () => {
    const { container } = render(
      <div>
        <AirfoilSelector label="" value="naca0015" id="airfoil-root" />
        <AirfoilSelector label="" value="e423" id="airfoil-tip" />
      </div>,
    );
    const rootTrigger = container.querySelector("#airfoil-root");
    const tipTrigger = container.querySelector("#airfoil-tip");
    expect(rootTrigger).not.toBeNull();
    expect(tipTrigger).not.toBeNull();
    // They must not be the same element
    expect(rootTrigger).not.toBe(tipTrigger);
  });

  it("id must not be empty ('airfoil-' with empty label causes duplicate-id violation)", () => {
    // This test asserts that when id='airfoil-root' is passed, the button id
    // is 'airfoil-root' and NOT the fallback 'airfoil-' (empty label fallback).
    const { container } = render(
      <AirfoilSelector label="" value="naca0015" id="airfoil-root" />,
    );
    const trigger = container.querySelector("button[id]");
    expect(trigger?.id).toBe("airfoil-root");
    expect(trigger?.id).not.toBe("airfoil-");
  });
});

// ── AirfoilPreviewConfigPanel: no duplicate ids on root/tip selectors ─

describe("AirfoilPreviewConfigPanel — no duplicate AirfoilSelector ids (ITEM 6)", () => {
  const baseProps = {
    rootAirfoil: "naca0015",
    tipAirfoil: "e423",
    onRootAirfoilChange: vi.fn(),
    onTipAirfoilChange: vi.fn(),
    isRunning: false,
    segmentIndex: 0,
    segmentCount: 1,
    onSegmentChange: vi.fn(),
    segmentProps: {},
    velocity: 14,
    onVelocityChange: vi.fn(),
    rootRe: 200000,
    tipRe: 150000,
    onRootReChange: vi.fn(),
    onTipReChange: vi.fn(),
    rootChordMm: 200,
    tipChordMm: 150,
    isDirty: false,
    isSaving: false,
    onSave: vi.fn(),
    onRevert: vi.fn(),
    onBack: vi.fn(),
  };

  it("root AirfoilSelector trigger has id='airfoil-root'", () => {
    const { container } = render(<AirfoilPreviewConfigPanel {...baseProps} />);
    const rootTrigger = container.querySelector("#airfoil-root");
    expect(rootTrigger).not.toBeNull();
    expect(rootTrigger?.tagName.toLowerCase()).toBe("button");
  });

  it("tip AirfoilSelector trigger has id='airfoil-tip'", () => {
    const { container } = render(<AirfoilPreviewConfigPanel {...baseProps} />);
    const tipTrigger = container.querySelector("#airfoil-tip");
    expect(tipTrigger).not.toBeNull();
    expect(tipTrigger?.tagName.toLowerCase()).toBe("button");
  });

  it("root and tip selector ids are DISTINCT (no duplicate-id violation)", () => {
    const { container } = render(<AirfoilPreviewConfigPanel {...baseProps} />);
    const rootTrigger = container.querySelector("#airfoil-root");
    const tipTrigger = container.querySelector("#airfoil-tip");
    expect(rootTrigger).not.toBeNull();
    expect(tipTrigger).not.toBeNull();
    // Distinct elements
    expect(rootTrigger).not.toBe(tipTrigger);
  });

  it("root selector label is associated with id='airfoil-root' via htmlFor", () => {
    const { container } = render(<AirfoilPreviewConfigPanel {...baseProps} />);
    const label = container.querySelector('label[for="airfoil-root"]');
    expect(label).not.toBeNull();
  });

  it("tip selector label is associated with id='airfoil-tip' via htmlFor", () => {
    const { container } = render(<AirfoilPreviewConfigPanel {...baseProps} />);
    const label = container.querySelector('label[for="airfoil-tip"]');
    expect(label).not.toBeNull();
  });

  it("there are no buttons with an empty id attribute", () => {
    const { container } = render(<AirfoilPreviewConfigPanel {...baseProps} />);
    // Collect all buttons that have an id attribute
    const buttonsWithId = container.querySelectorAll("button[id]");
    const emptyIds = Array.from(buttonsWithId).filter((btn) => !btn.id);
    expect(emptyIds).toHaveLength(0);
  });

  it("no two elements share the same non-empty id", () => {
    const { container } = render(<AirfoilPreviewConfigPanel {...baseProps} />);
    const elements = container.querySelectorAll("[id]");
    const ids = Array.from(elements).map((el) => el.id).filter(Boolean);
    const uniqueIds = new Set(ids);
    expect(ids.length).toBe(uniqueIds.size);
  });
});
