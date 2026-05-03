import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import type { PlanStepNode } from "@/components/workbench/PlanTree";
import type { CreatorInfo } from "@/hooks/useCreators";

// Mock lucide-react icons used by EditParamsModal
vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return { ArrowRight: icon, ArrowLeft: icon, X: icon, RotateCcw: icon };
});

// Mock useDialog — jsdom doesn't support <dialog>.showModal()
vi.mock("@/hooks/useDialog", () => ({
  useDialog: (_open: boolean, onClose: () => void) => ({
    dialogRef: { current: null },
    handleClose: onClose,
  }),
}));

// Mock CreatorParameterForm — render a stub that exposes onChange
let capturedOnChange: ((key: string, value: unknown) => void) | null = null;
vi.mock("@/components/workbench/CreatorParameterForm", () => ({
  CreatorParameterForm: (props: {
    onChange: (key: string, value: unknown) => void;
  }) => {
    capturedOnChange = props.onChange;
    return React.createElement("div", { "data-testid": "param-form" });
  },
}));

// Mock resolveNodeShapes — not relevant for these tests
vi.mock("@/lib/planTreeUtils", async (importOriginal) => {
  const orig =
    await importOriginal<typeof import("@/lib/planTreeUtils")>();
  return {
    ...orig,
    resolveNodeShapes: () => ({ inputs: [], outputs: [] }),
  };
});

import { EditParamsModal } from "@/components/workbench/construction-plans/EditParamsModal";

function makeNode(overrides: Partial<PlanStepNode> = {}): PlanStepNode {
  return {
    $TYPE: "SomeCreator",
    creator_id: "original-id",
    ...overrides,
  } as PlanStepNode;
}

function makeCreatorInfo(overrides: Partial<CreatorInfo> = {}): CreatorInfo {
  return {
    class_name: "SomeCreator",
    category: "wing",
    description: null,
    parameters: [
      {
        name: "span",
        type: "number",
        default: 1000,
        required: true,
        description: null,
        options: null,
      },
    ],
    outputs: [],
    suggested_id: "wing_{span}",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  capturedOnChange = null;
});

describe("EditParamsModal — reset button", () => {
  it("does not show reset button when dirty but suggested_id is null", () => {
    const node = makeNode({ _creatorIdDirty: true });
    const creator = makeCreatorInfo({ suggested_id: null });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );

    expect(screen.queryByTitle("Reset to auto-derived ID")).toBeNull();
  });

  it("shows reset button when dirty and suggested_id exists", () => {
    const node = makeNode({ _creatorIdDirty: true });
    const creator = makeCreatorInfo({ suggested_id: "wing_{span}" });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );

    expect(screen.queryByTitle("Reset to auto-derived ID")).not.toBeNull();
  });

  it("does not show reset button when not dirty", () => {
    const node = makeNode();
    const creator = makeCreatorInfo({ suggested_id: "wing_{span}" });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );

    expect(screen.queryByTitle("Reset to auto-derived ID")).toBeNull();
  });

  it("does not show reset button when creatorInfo is null", () => {
    const node = makeNode({ _creatorIdDirty: true });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={null}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );

    expect(screen.queryByTitle("Reset to auto-derived ID")).toBeNull();
  });

  it("does not show reset button when suggested_id is empty string", () => {
    const node = makeNode({ _creatorIdDirty: true });
    const creator = makeCreatorInfo({ suggested_id: "" as string | null });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );

    expect(screen.queryByTitle("Reset to auto-derived ID")).toBeNull();
  });
});

describe("EditParamsModal — dirty state transitions", () => {
  it("typing into ID field sets dirty and blocks auto-derivation on param change", async () => {
    const user = userEvent.setup();
    const node = makeNode();
    const creator = makeCreatorInfo({ suggested_id: "wing_{span}" });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );

    const idInput = screen.getByLabelText("ID") as HTMLInputElement;

    // Type into the ID field — should become dirty
    await user.clear(idInput);
    await user.type(idInput, "my-custom-id");
    expect(idInput.value).toBe("my-custom-id");

    // Now change a param — ID should NOT auto-derive because dirty
    act(() => { capturedOnChange?.("span", 2000); });
    expect(idInput.value).toBe("my-custom-id");
  });

  it("auto-derives ID from template when param changes and not dirty", () => {
    const node = makeNode();
    const creator = makeCreatorInfo({ suggested_id: "wing_{span}" });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );

    const idInput = screen.getByLabelText("ID") as HTMLInputElement;

    // Change param without touching ID — should auto-derive
    act(() => { capturedOnChange?.("span", 2000); });
    expect(idInput.value).toBe("wing_2000");
  });
});

describe("EditParamsModal — reset behavior", () => {
  it("clicking reset clears dirty and re-derives ID from template", async () => {
    const user = userEvent.setup();
    const node = makeNode({ _creatorIdDirty: true });
    const creator = makeCreatorInfo({ suggested_id: "wing_{span}" });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );

    const idInput = screen.getByLabelText("ID") as HTMLInputElement;
    // Type custom value
    await user.clear(idInput);
    await user.type(idInput, "custom-id");
    expect(idInput.value).toBe("custom-id");

    // Click reset
    const resetBtn = screen.getByTitle("Reset to auto-derived ID");
    await user.click(resetBtn);

    // ID should be resolved from template with current param values
    // Default span=1000, so template "wing_{span}" → "wing_1000"
    expect(idInput.value).toBe("wing_1000");

    // Reset button should disappear (dirty=false)
    expect(screen.queryByTitle("Reset to auto-derived ID")).toBeNull();
  });
});

describe("EditParamsModal — save payload", () => {
  it("sends _creatorIdDirty: true when ID was manually edited", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    const node = makeNode();
    const creator = makeCreatorInfo({ suggested_id: "wing_{span}" });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={onSave}
      />,
    );

    // Type into ID field to set dirty
    const idInput = screen.getByLabelText("ID") as HTMLInputElement;
    await user.clear(idInput);
    await user.type(idInput, "my-id");

    // Click save
    await user.click(screen.getByText("Save"));
    await vi.waitFor(() => expect(onSave).toHaveBeenCalled());

    const [path, params] = onSave.mock.calls[0];
    expect(path).toBe("/0");
    expect(params.creator_id).toBe("my-id");
    expect(params._creatorIdDirty).toBe(true);
  });

  it("forwards pre-existing dirty flag on save without editing", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    const node = makeNode({ _creatorIdDirty: true });
    const creator = makeCreatorInfo({ suggested_id: "wing_{span}" });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={onSave}
      />,
    );

    // Save without editing anything
    await user.click(screen.getByText("Save"));
    await vi.waitFor(() => expect(onSave).toHaveBeenCalled());

    const [, params] = onSave.mock.calls[0];
    expect(params._creatorIdDirty).toBe(true);
  });

  it("omits _creatorIdDirty after reset and save", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    const node = makeNode({ _creatorIdDirty: true });
    const creator = makeCreatorInfo({ suggested_id: "wing_{span}" });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={onSave}
      />,
    );

    // Click reset to clear dirty
    const resetBtn = screen.getByTitle("Reset to auto-derived ID");
    await user.click(resetBtn);

    // Save
    await user.click(screen.getByText("Save"));
    await vi.waitFor(() => expect(onSave).toHaveBeenCalled());

    const [, params] = onSave.mock.calls[0];
    expect(params._creatorIdDirty).toBeUndefined();
  });

  it("omits _creatorIdDirty when ID was not manually edited", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    const node = makeNode();
    const creator = makeCreatorInfo({ suggested_id: "wing_{span}" });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={onSave}
      />,
    );

    // Save without editing ID
    await user.click(screen.getByText("Save"));
    await vi.waitFor(() => expect(onSave).toHaveBeenCalled());

    const [, params] = onSave.mock.calls[0];
    expect(params._creatorIdDirty).toBeUndefined();
  });
});
