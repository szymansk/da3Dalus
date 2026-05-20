import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => ({
  Info: (props: Record<string, unknown>) => (
    <svg data-testid="info-icon" {...props} />
  ),
}));

import { TaillessBanner } from "../components/workbench/TaillessBanner";

describe("TaillessBanner (gh-581)", () => {
  it("renders the tailless UX banner with the expected design copy", () => {
    render(<TaillessBanner />);
    // Anchor sentence — flags the configuration to the user
    expect(screen.getByText(/Tailless configuration/i)).toBeInTheDocument();
    // Tail-volume sizing not applicable — explains the missing UI
    expect(
      screen.getByText(/Tail-volume\s+sizing not applicable/i),
    ).toBeInTheDocument();
    // Pitch-trim mechanisms call-out (hybrid preferred per Apogee)
    expect(screen.getByText(/hybrid \(preferred\)/i)).toBeInTheDocument();
    // Tighter SM corridor (5–10 % MAC) — see #579
    expect(screen.getByText(/SM target 5–10 % MAC/i)).toBeInTheDocument();
  });

  it("uses the status role so screen readers announce it without blocking", () => {
    render(<TaillessBanner />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("exposes a stable test id for higher-level integration tests", () => {
    render(<TaillessBanner />);
    expect(screen.getByTestId("tailless-banner")).toBeInTheDocument();
  });
});
