import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ExpertView } from "@/components/expert/ExpertView";

const useCanonFleet = vi.fn();
vi.mock("@/hooks/useCanonFleet", () => ({ useCanonFleet: () => useCanonFleet() }));

const FLEET = [
  { id: "bryan", name: "BRYAN", mass_kg: 0.151, flap_deflections: {} },
  { id: "rv-7", name: "RV-7", mass_kg: 0.5, flap_deflections: { "flap-deflection-landing": 30 } },
];

function frameSrc(): URL {
  const frame = screen.getByTitle(/canon navigator/i);
  return new URL(frame.getAttribute("src")!, "http://app.test");
}

describe("ExpertView", () => {
  beforeEach(() => {
    useCanonFleet.mockReturnValue({ fleet: FLEET, error: undefined, isLoading: false });
  });

  it("carries the development label of ADR 0030", () => {
    render(<ExpertView />);
    expect(screen.getByRole("note")).toHaveTextContent(
      "Canon/kernel view (development), experts only",
    );
  });

  it("hosts the connected navigator for the first aircraft of the fleet", () => {
    render(<ExpertView />);
    const src = frameSrc();
    expect(src.pathname).toBe("/canon-navigator.html");
    expect(src.searchParams.get("connected")).toBe("1");
    expect(src.searchParams.get("aircraft")).toBe("bryan");
    expect(src.searchParams.get("api")).toMatch(/^https?:\/\//);
    expect(screen.getByText("0.151 kg")).toBeInTheDocument();
  });

  it("offers every fleet aircraft and reconnects the navigator on a change", async () => {
    render(<ExpertView />);
    const picker = screen.getByRole("combobox", { name: "Aircraft" });
    expect(screen.getAllByRole("option").map((o) => o.textContent)).toEqual(["BRYAN", "RV-7"]);
    await userEvent.selectOptions(picker, "rv-7");
    expect(frameSrc().searchParams.get("aircraft")).toBe("rv-7");
    expect(screen.getByText("0.5 kg")).toBeInTheDocument();
  });

  it("shows no frame while the fleet loads", () => {
    useCanonFleet.mockReturnValue({ fleet: [], error: undefined, isLoading: true });
    render(<ExpertView />);
    expect(screen.queryByTitle(/canon navigator/i)).toBeNull();
    expect(screen.getByText(/Loading the fleet/)).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Aircraft" })).toBeDisabled();
  });

  it("says when the fleet cannot be loaded", () => {
    useCanonFleet.mockReturnValue({ fleet: [], error: new Error("503 down"), isLoading: false });
    render(<ExpertView />);
    expect(screen.getByRole("alert")).toHaveTextContent("The fleet could not be loaded: 503 down");
    expect(screen.queryByTitle(/canon navigator/i)).toBeNull();
  });
});
