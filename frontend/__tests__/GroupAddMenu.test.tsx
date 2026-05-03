/**
 * Tests for the popover-style add menu attached to each group row
 * in the Component Tree (gh#57-40g).
 *
 * The menu surfaces three options:
 *   1. "New Group"                — opens an inline input
 *   2. "Assign COTS Component"    — opens CotsPickerDialog
 *   3. "Assign Construction Part" — disabled until gh#57-wvg (D4) ships
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    FolderPlus: icon, Package: icon, Box: icon,
    Plus: icon, X: icon, Check: icon,
  };
});

import { GroupAddMenu } from "@/components/workbench/GroupAddMenu";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("GroupAddMenu", () => {
  it("shows all three options", () => {
    render(
      <GroupAddMenu
        groupName="main_wing"
        onNewGroup={vi.fn()}
        onAssignCots={vi.fn()}
        onAssignConstructionPart={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText("New Group")).toBeDefined();
    expect(screen.getByText("Assign COTS Component")).toBeDefined();
    expect(screen.getByText("Assign Construction Part")).toBeDefined();
  });

  it("shows the group name as context in the header", () => {
    render(
      <GroupAddMenu
        groupName="avionics"
        onNewGroup={vi.fn()}
        onAssignCots={vi.fn()}
        onAssignConstructionPart={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    // The group name appears somewhere (e.g. "Add to avionics")
    expect(screen.getByText(/avionics/)).toBeDefined();
  });

  it("calls onNewGroup (but not onClose) when 'New Group' is clicked", async () => {
    const user = userEvent.setup();
    const onNewGroup = vi.fn();
    const onClose = vi.fn();
    render(
      <GroupAddMenu
        groupName="main_wing"
        onNewGroup={onNewGroup}
        onAssignCots={vi.fn()}
        onAssignConstructionPart={vi.fn()}
        onClose={onClose}
      />,
    );

    await user.click(screen.getByText("New Group"));

    // The parent is responsible for dismissing the menu (typically by
    // transitioning into another state); GroupAddMenu must NOT auto-close.
    expect(onNewGroup).toHaveBeenCalledTimes(1);
    expect(onClose).not.toHaveBeenCalled();
  });

  it("calls onAssignCots (but not onClose) when 'Assign COTS Component' is clicked", async () => {
    const user = userEvent.setup();
    const onAssignCots = vi.fn();
    const onClose = vi.fn();
    render(
      <GroupAddMenu
        groupName="main_wing"
        onNewGroup={vi.fn()}
        onAssignCots={onAssignCots}
        onAssignConstructionPart={vi.fn()}
        onClose={onClose}
      />,
    );

    await user.click(screen.getByText("Assign COTS Component"));

    expect(onAssignCots).toHaveBeenCalledTimes(1);
    expect(onClose).not.toHaveBeenCalled();
  });

  it("disables 'Assign Construction Part' when constructionPartsEnabled=false", async () => {
    const user = userEvent.setup();
    const onAssign = vi.fn();
    render(
      <GroupAddMenu
        groupName="main_wing"
        onNewGroup={vi.fn()}
        onAssignCots={vi.fn()}
        onAssignConstructionPart={onAssign}
        onClose={vi.fn()}
        constructionPartsEnabled={false}
      />,
    );

    // Clicking the disabled item must not fire the callback
    await user.click(screen.getByText("Assign Construction Part"));
    expect(onAssign).not.toHaveBeenCalled();
  });

  it("calls onClose when the Escape key is pressed", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <GroupAddMenu
        groupName="main_wing"
        onNewGroup={vi.fn()}
        onAssignCots={vi.fn()}
        onAssignConstructionPart={vi.fn()}
        onClose={onClose}
      />,
    );
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("enables 'Assign Construction Part' when constructionPartsEnabled=true", async () => {
    const user = userEvent.setup();
    const onAssign = vi.fn();
    const onClose = vi.fn();
    render(
      <GroupAddMenu
        groupName="main_wing"
        onNewGroup={vi.fn()}
        onAssignCots={vi.fn()}
        onAssignConstructionPart={onAssign}
        onClose={onClose}
        constructionPartsEnabled={true}
      />,
    );

    await user.click(screen.getByText("Assign Construction Part"));
    expect(onAssign).toHaveBeenCalledTimes(1);
    expect(onClose).not.toHaveBeenCalled();
  });
});
