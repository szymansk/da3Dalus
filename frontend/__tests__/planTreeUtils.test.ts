import { describe, it, expect } from "vitest";
import type { PlanStepNode } from "@/components/workbench/PlanTree";
import type { CreatorInfo } from "@/hooks/useCreators";
import {
  getStepAtPath,
  deleteStepAtPath,
  insertStepAtPath,
  updateNodeAtPath,
  collectAvailableShapeKeys,
  resolveIdTemplate,
  computeReorderTargetPath,
} from "@/lib/planTreeUtils";

function makeNode(type: string, id: string, successors: PlanStepNode[] = []): PlanStepNode {
  return { $TYPE: type, creator_id: id, successors };
}

const root = makeNode("ConstructionRootNode", "root", [
  makeNode("WingCreator", "wing1"),
  makeNode("FuselageCreator", "fuse1"),
  makeNode("ExportCreator", "export1"),
]);

describe("getStepAtPath", () => {
  it("returns root for 'root' path", () => {
    expect(getStepAtPath(root, "root")).toBe(root);
  });

  it("returns a direct child", () => {
    expect(getStepAtPath(root, "root.1")).toBe(root.successors![1]);
  });

  it("returns null for invalid path", () => {
    expect(getStepAtPath(root, "root.5")).toBeNull();
  });

  it("navigates nested successors", () => {
    const nested = makeNode("Root", "root", [
      makeNode("A", "a", [makeNode("B", "b")]),
    ]);
    expect(getStepAtPath(nested, "root.0.0")?.creator_id).toBe("b");
  });
});

describe("deleteStepAtPath", () => {
  it("clears all successors when path is 'root'", () => {
    const result = deleteStepAtPath(root, "root");
    expect(result.successors).toEqual([]);
    // Original unchanged
    expect(root.successors!.length).toBe(3);
  });

  it("removes the correct child by index", () => {
    const result = deleteStepAtPath(root, "root.1");
    expect(result.successors!.length).toBe(2);
    expect(result.successors![0].creator_id).toBe("wing1");
    expect(result.successors![1].creator_id).toBe("export1");
  });
});

describe("insertStepAtPath", () => {
  const newStep = makeNode("NewCreator", "new1");

  it("appends to root when path is 'root'", () => {
    const result = insertStepAtPath(root, "root", newStep);
    expect(result.successors!.length).toBe(4);
    expect(result.successors![3].creator_id).toBe("new1");
  });

  it("inserts after the specified index", () => {
    const result = insertStepAtPath(root, "root.0", newStep);
    expect(result.successors!.length).toBe(4);
    expect(result.successors![1].creator_id).toBe("new1");
    expect(result.successors![2].creator_id).toBe("fuse1");
  });
});

describe("updateNodeAtPath", () => {
  it("replaces root when path is 'root'", () => {
    const replacement = makeNode("X", "x");
    const result = updateNodeAtPath(root, "root", replacement);
    expect(result.creator_id).toBe("x");
  });

  it("replaces a direct child", () => {
    const replacement = makeNode("Updated", "updated");
    const result = updateNodeAtPath(root, "root.1", replacement);
    expect(result.successors![1].creator_id).toBe("updated");
    expect(result.successors![0].creator_id).toBe("wing1");
  });
});

describe("collectAvailableShapeKeys", () => {
  const creators: CreatorInfo[] = [
    {
      class_name: "WingCreator",
      category: "wing",
      description: null,
      parameters: [],
      outputs: [{ key: "{id}_shape", description: "wing shape" }],
      suggested_id: null,
    },
  ];

  it("returns empty array for null tree", () => {
    expect(collectAvailableShapeKeys(null, creators)).toEqual([]);
  });

  it("collects keys from creator outputs", () => {
    const keys = collectAvailableShapeKeys(root, creators);
    expect(keys).toContain("wing1_shape");
  });

  it("stops at stopPath", () => {
    const keys = collectAvailableShapeKeys(root, creators, "root.0");
    expect(keys).toEqual([]);
  });

  it("falls back to stepId when creator has no outputs", () => {
    const keys = collectAvailableShapeKeys(root, []);
    expect(keys).toEqual(["wing1", "fuse1", "export1"]);
  });
});

describe("resolveIdTemplate", () => {
  it("replaces placeholders with param values", () => {
    expect(resolveIdTemplate("{name}_wing", { name: "main" })).toBe("main_wing");
  });

  it("leaves unresolved placeholders intact", () => {
    expect(resolveIdTemplate("{name}_wing", {})).toBe("{name}_wing");
  });

  it("handles empty string params", () => {
    expect(resolveIdTemplate("{name}_wing", { name: "" })).toBe("{name}_wing");
  });
});

describe("computeReorderTargetPath", () => {
  it("adjusts when dragging forward in same parent", () => {
    expect(computeReorderTargetPath("root.0", "root.2")).toBe("root.1");
  });

  it("does not adjust when dragging backward", () => {
    expect(computeReorderTargetPath("root.2", "root.0")).toBe("root.0");
  });

  it("does not adjust across different parents", () => {
    expect(computeReorderTargetPath("root.0", "root.1.0")).toBe("root.1.0");
  });

  it("returns toPath unchanged for same-index siblings in different depth", () => {
    expect(computeReorderTargetPath("root.0.1", "root.1")).toBe("root.1");
  });
});
