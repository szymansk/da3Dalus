/**
 * Unit tests for the shared DialogField component (gh-936).
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { DialogField } from "@/components/workbench/DialogField";

describe("DialogField", () => {
  it("renders a labeled input", () => {
    render(<DialogField label="My Field" value="42" onChange={() => {}} />);
    expect(screen.getByLabelText("My Field")).toBeTruthy();
  });

  it("shows the supplied value in the input", () => {
    render(<DialogField label="Height" value="1.5" onChange={() => {}} />);
    expect((screen.getByLabelText("Height") as HTMLInputElement).value).toBe("1.5");
  });

  it("calls onChange when user types", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DialogField label="Position" value="" onChange={onChange} />);
    await user.type(screen.getByLabelText("Position"), "0.1");
    expect(onChange).toHaveBeenCalled();
  });

  it("renders suffix when provided", () => {
    render(<DialogField label="Speed" value="10" onChange={() => {}} suffix="m/s" />);
    expect(screen.getByText("m/s")).toBeTruthy();
  });

  it("does not render suffix element when suffix is omitted", () => {
    render(<DialogField label="X" value="5" onChange={() => {}} />);
    expect(screen.queryByText("m/s")).toBeNull();
  });

  it("uses type='number' by default", () => {
    render(<DialogField label="Num" value="3" onChange={() => {}} />);
    expect((screen.getByLabelText("Num") as HTMLInputElement).type).toBe("number");
  });

  it("uses type='text' when specified", () => {
    render(<DialogField label="Name" value="foo" onChange={() => {}} type="text" />);
    expect((screen.getByLabelText("Name") as HTMLInputElement).type).toBe("text");
  });

  it("forwards placeholder to input", () => {
    render(<DialogField label="Tip" value="" onChange={() => {}} placeholder="same as root" />);
    expect((screen.getByLabelText("Tip") as HTMLInputElement).placeholder).toBe("same as root");
  });

  it("auto-generates unique id so label htmlFor matches input id", () => {
    render(<DialogField label="Unique" value="" onChange={() => {}} />);
    const input = screen.getByLabelText("Unique");
    expect(input).toBeTruthy();
  });
});
