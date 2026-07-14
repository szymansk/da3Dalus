/**
 * Coverage for MetricColumn's interactive rendering, touched by the
 * SonarCloud chore cleanup (S1082 → real <button> instead of role="button").
 *
 * - "tile" / "tab" (collapsed, non-large) modes must render a real, keyboard-
 *   accessible <button> whose activation calls onActivate.
 * - "large" mode must NOT be a button (it wraps a nested collapse control).
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Gauge } from "lucide-react";

import { MetricColumn } from "@/components/workbench/metrics-dashboard/MetricColumn";

function renderColumn(mode: "tab" | "tile" | "large", onActivate = vi.fn()) {
  render(
    <MetricColumn
      title="Speed"
      icon={Gauge}
      mode={mode}
      onActivate={onActivate}
      onCollapse={vi.fn()}
      headline="v_stall 9 m/s"
      tile={<div>tile-body</div>}
      large={<div>large-body</div>}
    />,
  );
  return onActivate;
}

describe("MetricColumn interactive element (S1082)", () => {
  it("renders a real <button> in tile mode and fires onActivate on click", () => {
    const onActivate = renderColumn("tile");
    const col = screen.getByTestId("metric-col-speed");
    expect(col.tagName).toBe("BUTTON");
    expect(col).toHaveAttribute("type", "button");
    expect(col).toHaveAttribute("aria-label", "Expand Speed");
    fireEvent.click(col);
    expect(onActivate).toHaveBeenCalledTimes(1);
  });

  it("renders a real <button> in tab mode and fires onActivate on click", () => {
    const onActivate = renderColumn("tab");
    // tab mode has no data-testid; it is the only button rendered here.
    const btn = screen.getByRole("button", { name: /Speed/i });
    expect(btn.tagName).toBe("BUTTON");
    fireEvent.click(btn);
    expect(onActivate).toHaveBeenCalledTimes(1);
  });

  it("is native-keyboard accessible in tile mode (Enter activates a button)", () => {
    renderColumn("tile");
    const col = screen.getByTestId("metric-col-speed");
    // A native <button> is activated by the browser on Enter/Space via a
    // synthetic click — assert the element is focusable and a button so the
    // platform provides keyboard activation (no manual onKeyDown needed).
    col.focus();
    expect(col).toHaveFocus();
    expect(col.tagName).toBe("BUTTON");
  });

  it("does not render the large section as a button", () => {
    renderColumn("large");
    const col = screen.getByTestId("metric-col-speed");
    expect(col.tagName).toBe("SECTION");
    expect(col).not.toHaveAttribute("role", "button");
  });
});
