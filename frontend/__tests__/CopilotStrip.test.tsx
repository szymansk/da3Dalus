import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { CopilotStrip } from "@/components/workbench/CopilotStrip";

describe("CopilotStrip", () => {
  it("renders the slim bar with 'Ask the copilot…' label", () => {
    render(<CopilotStrip />);
    expect(screen.getByText("Ask the copilot…")).toBeInTheDocument();
  });

  it("renders a Send button in the slim bar and a toggle button", () => {
    render(<CopilotStrip />);
    // The slim-bar Send button has aria-label="Send"
    const sendBtns = screen.getAllByRole("button", { name: "Send" });
    expect(sendBtns.length).toBeGreaterThanOrEqual(1);
    expect(
      screen.getByRole("button", { name: "Expand copilot panel" })
    ).toBeInTheDocument();
  });

  it("starts collapsed: panel is present in DOM but visually hidden (grid-rows-[0fr])", () => {
    render(<CopilotStrip />);
    // The toggle button has aria-expanded=false initially.
    const toggleBtn = screen.getByRole("button", { name: "Expand copilot panel" });
    expect(toggleBtn).toHaveAttribute("aria-expanded", "false");

    // The panel container has the collapsed CSS class.
    const panel = screen.getByTestId("copilot-panel");
    const slideWrapper = panel.parentElement?.parentElement;
    expect(slideWrapper?.className).toContain("grid-rows-[0fr]");
  });

  it("expands on first click: aria-expanded becomes true and panel is shown", async () => {
    const user = userEvent.setup();
    render(<CopilotStrip />);

    const toggleBtn = screen.getByRole("button", { name: "Expand copilot panel" });
    await user.click(toggleBtn);

    // Button now reports aria-expanded=true and its label switches.
    expect(
      screen.getByRole("button", { name: "Collapse copilot panel" })
    ).toHaveAttribute("aria-expanded", "true");

    // Slide wrapper now has the open CSS class.
    const panel = screen.getByTestId("copilot-panel");
    const slideWrapper = panel.parentElement?.parentElement;
    expect(slideWrapper?.className).toContain("grid-rows-[1fr]");
  });

  it("collapses again on second click", async () => {
    const user = userEvent.setup();
    render(<CopilotStrip />);

    const expandBtn = screen.getByRole("button", { name: "Expand copilot panel" });
    await user.click(expandBtn);

    const collapseBtn = screen.getByRole("button", { name: "Collapse copilot panel" });
    await user.click(collapseBtn);

    const toggleBtn = screen.getByRole("button", { name: "Expand copilot panel" });
    expect(toggleBtn).toHaveAttribute("aria-expanded", "false");

    const panel = screen.getByTestId("copilot-panel");
    const slideWrapper = panel.parentElement?.parentElement;
    expect(slideWrapper?.className).toContain("grid-rows-[0fr]");
  });

  it("shows textarea placeholder and Send button inside expanded panel", async () => {
    const user = userEvent.setup();
    render(<CopilotStrip />);

    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    expect(
      screen.getByPlaceholderText("Ask a design question…")
    ).toBeInTheDocument();
  });
});
