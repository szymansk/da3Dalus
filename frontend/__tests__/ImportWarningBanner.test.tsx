/**
 * Unit tests for ImportWarningBanner (gh-648).
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ImportWarningBanner from "@/components/workbench/ImportWarningBanner";

const STORAGE_PREFIX = "vsp-warnings-dismissed-";

const sample = (severity: "info" | "warning" | "error") => ({
  component_type: "PROP",
  component_name: "MainProp",
  reason: "Propellers not yet supported (Phase 2)",
  severity,
});

describe("ImportWarningBanner", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nothing for an empty warning list", () => {
    const { container } = render(
      <ImportWarningBanner warnings={[]} aeroplaneUuid="uuid-1" />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders warnings with severity badges", () => {
    render(
      <ImportWarningBanner
        warnings={[sample("warning")]}
        aeroplaneUuid="uuid-1"
      />,
    );
    const banner = screen.getByTestId("openvsp-warning-banner");
    expect(banner).toBeInTheDocument();
    expect(screen.getByText(/Propellers not yet supported/)).toBeInTheDocument();
    expect(screen.getByText("PROP")).toBeInTheDocument();
    expect(screen.getByText("WARNING")).toBeInTheDocument();
  });

  it("renders pluralised header when multiple warnings", () => {
    render(
      <ImportWarningBanner
        warnings={[sample("warning"), sample("info")]}
        aeroplaneUuid="uuid-1"
      />,
    );
    expect(
      screen.getByText(/2 components were not fully imported/),
    ).toBeInTheDocument();
  });

  it("dismiss button hides banner and persists to localStorage", () => {
    render(
      <ImportWarningBanner
        warnings={[sample("warning")]}
        aeroplaneUuid="uuid-42"
      />,
    );
    fireEvent.click(screen.getByTestId("openvsp-warning-dismiss"));
    expect(
      screen.queryByTestId("openvsp-warning-banner"),
    ).not.toBeInTheDocument();
    expect(window.localStorage.getItem(`${STORAGE_PREFIX}uuid-42`)).toBe(
      "true",
    );
  });

  it("respects an existing dismissed flag in localStorage", () => {
    window.localStorage.setItem(`${STORAGE_PREFIX}uuid-99`, "true");
    render(
      <ImportWarningBanner
        warnings={[sample("warning")]}
        aeroplaneUuid="uuid-99"
      />,
    );
    expect(
      screen.queryByTestId("openvsp-warning-banner"),
    ).not.toBeInTheDocument();
  });

  it("uses red frame when an error severity is present", () => {
    render(
      <ImportWarningBanner
        warnings={[sample("info"), sample("error")]}
        aeroplaneUuid="uuid-1"
      />,
    );
    const banner = screen.getByTestId("openvsp-warning-banner");
    expect(banner.className).toContain("border-red-500");
  });

  it("uses orange frame when only warnings are present", () => {
    render(
      <ImportWarningBanner
        warnings={[sample("warning"), sample("info")]}
        aeroplaneUuid="uuid-1"
      />,
    );
    const banner = screen.getByTestId("openvsp-warning-banner");
    expect(banner.className).toContain("border-[#FF8400]");
  });

  it("uses neutral frame when only info is present", () => {
    render(
      <ImportWarningBanner
        warnings={[sample("info")]}
        aeroplaneUuid="uuid-1"
      />,
    );
    const banner = screen.getByTestId("openvsp-warning-banner");
    expect(banner.className).toContain("border-neutral-600");
  });
});
