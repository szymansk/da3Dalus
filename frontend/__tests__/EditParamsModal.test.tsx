import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
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
});

describe("EditParamsModal — dirty state transitions", () => {
  it("typing into ID field sets dirty and blocks auto-derivation on param change", () => {
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
    fireEvent.change(idInput, { target: { value: "my-custom-id" } });
    expect(idInput.value).toBe("my-custom-id");

    // Now change a param — ID should NOT auto-derive because dirty
    act(() => { capturedOnChange?.("span", 2000); });
    expect(idInput.value).toBe("my-custom-id");
  });
});
