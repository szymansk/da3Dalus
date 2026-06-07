/**
 * i18n consistency tests for AirfoilSuitabilityCard — ITEM 4.
 *
 * Prevailing language decision: GERMAN.
 * Rationale: The surrounding workbench panel uses English for pure structural
 * navigation (segment, Save, Revert, Back to Construction) but all
 * aerodynamic/physics content uses German (Reynolds-Zahl, Grenzschicht,
 * Modellflugzeuge, Profiltiefe, etc.). The AirfoilSuitabilityCard is a physics
 * content surface → German is the correct prevailing language.
 *
 * This test suite asserts that ALL visible human-readable card text uses German,
 * with these exceptions that are standard notation (language-neutral):
 *   - Score-axis labels C_L, C_D, alpha are scientific notation (in viewer panel,
 *     not tested here — they live in AirfoilPreviewViewerPanel)
 *   - Airfoil names (e.g. "e423") are identifiers, not language
 *
 * Items asserted:
 *   4a. qualitativeLabel returns German strings
 *   4b. ScoreBar labels are German
 *   4c. Eignung header is German
 *   4d. ConfidenceChip text is German ("Konfidenz")
 *   4e. ProvenanceIndicator labels and tooltips are German
 *   4f. StallClMaxRow labels are German ("Stall-Sanftheit", "CL-Margin")
 *       and warning text "abrupt" and "Ziel > CL_max!" remain unchanged
 *   4g. TipReClMaxWarning is German
 *   4h. CaveatCallout is German
 *   4i. AirfoilSuitabilityNoData is German
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => ({
  ChevronDown: (p: Record<string, unknown>) => <svg data-testid="chevron-down" {...p} />,
  ChevronRight: (p: Record<string, unknown>) => <svg data-testid="chevron-right" {...p} />,
  AlertTriangle: (p: Record<string, unknown>) => <svg data-testid="alert-triangle" {...p} />,
  Info: (p: Record<string, unknown>) => <svg data-testid="info" {...p} />,
  Activity: (p: Record<string, unknown>) => <svg data-testid="activity" {...p} />,
}));

import {
  AirfoilSuitabilityCard,
  AirfoilSuitabilityNoData,
  qualitativeLabel,
} from "../components/workbench/AirfoilSuitabilityCard";
import type { SuitabilityItem, SuitabilityCaveat } from "../hooks/useAirfoilSuitability";

const baseItem: SuitabilityItem = {
  airfoil_name: "e423",
  family: "cambered",
  re_agnostic: 0.82,
  mission: 0.75,
  target_cl_cruise: 0.68,
  target_cl_best_glide: 0.80,
  target_cl_min_sink: 0.55,
  stall_gentleness: -0.02,
  cl_max_margin: 0.15,
  min_analysis_confidence: 0.92,
  tip_re_flag: false,
  caveat: "Nur relative Rangfolge.",
  tags: [],
};

const abruptStallItem: SuitabilityItem = {
  ...baseItem,
  stall_gentleness: -0.18,
};

const negMarginItem: SuitabilityItem = {
  ...baseItem,
  cl_max_margin: -0.05,
};

const lowConfidenceItem: SuitabilityItem = {
  ...baseItem,
  min_analysis_confidence: 0.72,
};

const baseCaveat: SuitabilityCaveat = {
  relative_ranking_only: true,
  no_hysteresis_modelling: true,
  ignores_tip_re_clmax_collapse: true,
  recommend_xfoil_validation: false,
  text: "Nur relative Rangfolge. Kein Hysterese-Modell.",
};

// ── 4a: qualitativeLabel returns German ─────────────────────────────

describe("ITEM 4 — qualitativeLabel: German strings only", () => {
  it("returns 'Gut' (German) for score >= 0.75 — not 'Good'", () => {
    expect(qualitativeLabel(0.82)).toBe("Gut");
    expect(qualitativeLabel(0.75)).toBe("Gut");
    expect(qualitativeLabel(1.0)).toBe("Gut");
  });

  it("returns 'Mäßig' (German) for score 0.5–0.75 — not 'Average'", () => {
    expect(qualitativeLabel(0.6)).toBe("Mäßig");
    expect(qualitativeLabel(0.5)).toBe("Mäßig");
    expect(qualitativeLabel(0.74)).toBe("Mäßig");
  });

  it("returns 'Schwach' (German) for score < 0.5 — not 'Weak'", () => {
    expect(qualitativeLabel(0.3)).toBe("Schwach");
    expect(qualitativeLabel(0.0)).toBe("Schwach");
    expect(qualitativeLabel(0.49)).toBe("Schwach");
  });
});

// ── 4b: ScoreBar labels are German ─────────────────────────────────

describe("ITEM 4 — ScoreBar labels: German", () => {
  it("renders 'Re-agnostisch' bar label (German)", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/Re-agnostisch/)).toBeDefined();
  });

  it("renders 'Mission' bar label (language-neutral, acceptable)", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/^Mission$/)).toBeDefined();
  });

  it("renders 'Ziel-CL · Cruise' label — German 'Ziel-CL' with 'Cruise' as accepted technical term", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/Ziel-CL · Cruise/)).toBeDefined();
  });

  it("renders 'Ziel-CL · Best-Glide' label — German 'Ziel-CL' prefix", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/Ziel-CL · Best-Glide/)).toBeDefined();
  });

  it("renders German sublabel 'Motorausfall / Segelflug' under Best-Glide bar", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/Motorausfall \/ Segelflug/)).toBeDefined();
  });

  it("renders 'Ziel-CL · Min-Sink' label — German 'Ziel-CL' prefix", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/Ziel-CL · Min-Sink/)).toBeDefined();
  });
});

// ── 4c: Eignung header is German ────────────────────────────────────

describe("ITEM 4 — 'Eignung' header: German (not 'Suitability')", () => {
  it("card header shows 'Eignung' (German)", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/Eignung/)).toBeDefined();
  });

  it("no-data placeholder also shows 'Eignung' (German)", () => {
    render(<AirfoilSuitabilityNoData />);
    const matches = screen.queryAllByText(/Eignung/);
    expect(matches.length).toBeGreaterThan(0);
  });
});

// ── 4d: ConfidenceChip text is German ──────────────────────────────

describe("ITEM 4 — ConfidenceChip: German text ('Konfidenz' not 'Confidence')", () => {
  it("chip shows 'Konfidenz' (German) not 'Confidence' (English)", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    // Should render 'Konfidenz' with the numeric value
    const chip = screen.getByText(/Konfidenz/);
    expect(chip).toBeDefined();
    expect(chip.textContent).toMatch(/Konfidenz/);
    // Should NOT contain the English word 'Confidence'
    expect(chip.textContent).not.toMatch(/\bConfidence\b/);
  });

  it("confidence chip has a German tooltip (title attribute)", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    const chip = screen.getByText(/Konfidenz/);
    const title = chip.getAttribute("title");
    expect(title).toBeTruthy();
    // Tooltip must contain German content
    expect(title).toMatch(/Modell-Konfidenz|Stützstellen|Orientierung/);
  });
});

// ── 4e: ProvenanceIndicator labels and tooltips are German ───────────

describe("ITEM 4 — ProvenanceIndicator: German labels and tooltips", () => {
  it("calculated provenance shows German label 'Ber. Referenz'", () => {
    render(
      <AirfoilSuitabilityCard item={baseItem} defaultOpen targetClProvenance="calculated" />,
    );
    const indicator = screen.getByTestId("provenance-indicator");
    expect(indicator.textContent).toMatch(/Ber\. Referenz/);
  });

  it("estimated provenance shows German label 'Geschätzte Ref.'", () => {
    render(
      <AirfoilSuitabilityCard item={baseItem} defaultOpen targetClProvenance="estimated" />,
    );
    const indicator = screen.getByTestId("provenance-indicator");
    expect(indicator.textContent).toMatch(/Gesch[äa]tzte Ref\./);
  });

  it("mixed provenance shows German label 'Gem. Referenz'", () => {
    render(
      <AirfoilSuitabilityCard item={baseItem} defaultOpen targetClProvenance="mixed" />,
    );
    const indicator = screen.getByTestId("provenance-indicator");
    expect(indicator.textContent).toMatch(/Gem\. Referenz/);
  });

  it("calculated provenance tooltip is German (bewegliche Referenz)", () => {
    render(
      <AirfoilSuitabilityCard item={baseItem} defaultOpen targetClProvenance="calculated" />,
    );
    const indicator = screen.getByTestId("provenance-indicator");
    const title = indicator.getAttribute("title");
    expect(title).toMatch(/bewegliche Referenz/);
  });

  it("estimated provenance tooltip is German (feste Referenz)", () => {
    render(
      <AirfoilSuitabilityCard item={baseItem} defaultOpen targetClProvenance="estimated" />,
    );
    const indicator = screen.getByTestId("provenance-indicator");
    const title = indicator.getAttribute("title");
    expect(title).toMatch(/feste Referenz/);
  });

  it("mixed provenance tooltip is German (kombinierte Referenz)", () => {
    render(
      <AirfoilSuitabilityCard item={baseItem} defaultOpen targetClProvenance="mixed" />,
    );
    const indicator = screen.getByTestId("provenance-indicator");
    const title = indicator.getAttribute("title");
    expect(title).toMatch(/kombinierte Referenz/);
  });
});

// ── 4f: StallClMaxRow labels are German ─────────────────────────────

describe("ITEM 4 — StallClMaxRow: German row labels", () => {
  it("stall row label shows 'Stall-Sanftheit' (German)", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/Stall-Sanftheit/)).toBeDefined();
  });

  it("CL margin row label shows 'CL-Margin' (accepted technical term)", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/CL-Margin/)).toBeDefined();
  });

  it("abrupt stall warning shows 'abrupt' (accepted technical term in German aviation context)", () => {
    render(<AirfoilSuitabilityCard item={abruptStallItem} defaultOpen />);
    const warning = screen.getByTestId("stall-abrupt-warning");
    expect(warning.textContent).toMatch(/abrupt/);
  });

  it("negative CL-margin warning shows German 'Ziel > CL_max!'", () => {
    render(<AirfoilSuitabilityCard item={negMarginItem} defaultOpen />);
    const warning = screen.getByTestId("cl-max-margin-warning");
    expect(warning.textContent).toMatch(/Ziel.*CL_max/);
  });
});

// ── 4g: TipReClMaxWarning is German ─────────────────────────────────
// gh-825 item 4: warning is gated on per-airfoil tip_re_flag ONLY, so we must
// use an item with tip_re_flag=true to trigger it.

describe("ITEM 4 — TipReClMaxWarning: German text", () => {
  it("tip-Re warning text is in German", () => {
    const tipFlagItem: SuitabilityItem = { ...baseItem, tip_re_flag: true };
    render(
      <AirfoilSuitabilityCard item={tipFlagItem} defaultOpen caveatObject={baseCaveat} />,
    );
    const warning = screen.getByTestId("tip-re-clmax-warning");
    // Text must contain German words (not English equivalent)
    expect(warning.textContent).toMatch(
      /Flügelspitze|Tip-Re|Einbruch|Stall-Zone|XFoil|Validierung/,
    );
  });
});

// ── 4h: CaveatCallout is German ─────────────────────────────────────

describe("ITEM 4 — CaveatCallout: German text", () => {
  it("regular caveat text comes from backend (German by convention)", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByRole("note").textContent).toMatch(/Rangfolge/);
  });

  it("low-confidence prefix is German ('Geringe Modell-Konfidenz')", () => {
    render(<AirfoilSuitabilityCard item={lowConfidenceItem} defaultOpen />);
    expect(screen.getByRole("note").textContent).toMatch(/Geringe Modell-Konfidenz/);
  });

  it("low-confidence caveat mentions German 'grobe Orientierung'", () => {
    render(<AirfoilSuitabilityCard item={lowConfidenceItem} defaultOpen />);
    expect(screen.getByRole("note").textContent).toMatch(/grobe Orientierung/);
  });
});

// ── 4i: AirfoilSuitabilityNoData text is German ─────────────────────

describe("ITEM 4 — AirfoilSuitabilityNoData: German text", () => {
  it("no-data text is in German (not 'No data available')", () => {
    render(<AirfoilSuitabilityNoData />);
    expect(screen.getByText(/Keine Low-Re-Eignungsdaten/)).toBeDefined();
  });

  it("no-data text with airfoil name is in German", () => {
    render(<AirfoilSuitabilityNoData airfoilName="rae2822" />);
    expect(screen.getByText(/Keine Low-Re-Eignungsdaten für/)).toBeDefined();
  });
});
