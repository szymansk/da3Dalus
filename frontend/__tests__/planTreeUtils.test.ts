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
  toBackendTree,
  fromBackendTree,
  appendChildAtPath,
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

describe("toBackendTree", () => {
  it("converts a root with no successors", () => {
    const frontend = makeNode("ConstructionRootNode", "root");
    const backend = toBackendTree(frontend);
    expect(backend.$TYPE).toBe("ConstructionRootNode");
    expect(backend.creator_id).toBe("root");
    expect(backend.loglevel).toBe(50);
    expect(backend.successors).toEqual({});
  });

  it("wraps each child in a ConstructionStepNode with creator", () => {
    const frontend: PlanStepNode = {
      $TYPE: "ConstructionRootNode",
      creator_id: "root",
      successors: [
        { $TYPE: "WingLoftCreator", creator_id: "main_wing.loft", offset: 0, connected: true, wing_index: "main_wing", wing_side: "BOTH", successors: [] },
      ],
    };
    const backend = toBackendTree(frontend);

    // successors is a dict keyed by creator_id
    expect(backend.successors).toBeTypeOf("object");
    expect(Array.isArray(backend.successors)).toBe(false);

    const step = (backend.successors as Record<string, Record<string, unknown>>)["main_wing.loft"];
    expect(step).toBeDefined();
    expect(step.$TYPE).toBe("ConstructionStepNode");
    expect(step.creator_id).toBe("main_wing.loft");
    expect(step.loglevel).toBe(50);

    // creator is nested inside the step node
    const creator = step.creator as Record<string, unknown>;
    expect(creator.$TYPE).toBe("WingLoftCreator");
    expect(creator.creator_id).toBe("main_wing.loft");
    expect(creator.offset).toBe(0);
    expect(creator.connected).toBe(true);
    expect(creator.wing_index).toBe("main_wing");
    expect(creator.wing_side).toBe("BOTH");
    expect(creator.loglevel).toBe(50);
  });

  it("preserves loglevel if already set on the node", () => {
    const frontend: PlanStepNode = {
      $TYPE: "ConstructionRootNode",
      creator_id: "root",
      loglevel: 10,
      successors: [
        { $TYPE: "WingLoftCreator", creator_id: "w1", loglevel: 20, successors: [] },
      ],
    };
    const backend = toBackendTree(frontend);
    expect(backend.loglevel).toBe(10);

    const step = (backend.successors as Record<string, Record<string, unknown>>)["w1"];
    const creator = step.creator as Record<string, unknown>;
    expect(creator.loglevel).toBe(20);
  });

  it("handles nested successors recursively", () => {
    const frontend: PlanStepNode = {
      $TYPE: "ConstructionRootNode",
      creator_id: "root",
      successors: [
        {
          $TYPE: "WingLoftCreator", creator_id: "w1",
          successors: [
            { $TYPE: "ExportCreator", creator_id: "e1", successors: [] },
          ],
        },
      ],
    };
    const backend = toBackendTree(frontend);
    const step = (backend.successors as Record<string, Record<string, unknown>>)["w1"];
    const nested = (step.successors as Record<string, Record<string, unknown>>)["e1"];
    expect(nested.$TYPE).toBe("ConstructionStepNode");
    expect((nested.creator as Record<string, unknown>).$TYPE).toBe("ExportCreator");
  });
});

describe("fromBackendTree", () => {
  it("converts a backend root with dict successors to frontend format", () => {
    const backend = {
      $TYPE: "ConstructionRootNode",
      creator_id: "root",
      loglevel: 50,
      successors: {
        "main_wing.loft": {
          $TYPE: "ConstructionStepNode",
          creator_id: "main_wing.loft",
          loglevel: 50,
          creator: {
            $TYPE: "WingLoftCreator",
            creator_id: "main_wing.loft",
            offset: 0,
            connected: true,
            loglevel: 10,
          },
          successors: {},
        },
      },
    };
    const frontend = fromBackendTree(backend);
    expect(frontend.$TYPE).toBe("ConstructionRootNode");
    expect(frontend.creator_id).toBe("root");
    expect(frontend.loglevel).toBe(50);
    expect(Array.isArray(frontend.successors)).toBe(true);
    expect(frontend.successors!.length).toBe(1);

    const child = frontend.successors![0];
    expect(child.$TYPE).toBe("WingLoftCreator");
    expect(child.creator_id).toBe("main_wing.loft");
    expect(child.offset).toBe(0);
    expect(child.connected).toBe(true);
    expect(child.loglevel).toBe(10);
  });

  it("passes through frontend format unchanged (array successors)", () => {
    const frontend: PlanStepNode = {
      $TYPE: "ConstructionRootNode",
      creator_id: "root",
      successors: [
        { $TYPE: "WingLoftCreator", creator_id: "w1", successors: [] },
      ],
    };
    const result = fromBackendTree(frontend);
    expect(result.successors).toEqual(frontend.successors);
  });

  it("handles nested dict successors recursively", () => {
    const backend = {
      $TYPE: "ConstructionRootNode",
      creator_id: "root",
      loglevel: 50,
      successors: {
        w1: {
          $TYPE: "ConstructionStepNode",
          creator_id: "w1",
          loglevel: 50,
          creator: { $TYPE: "WingLoftCreator", creator_id: "w1", loglevel: 50 },
          successors: {
            e1: {
              $TYPE: "ConstructionStepNode",
              creator_id: "e1",
              loglevel: 50,
              creator: { $TYPE: "ExportCreator", creator_id: "e1", loglevel: 50 },
              successors: {},
            },
          },
        },
      },
    };
    const frontend = fromBackendTree(backend);
    expect(frontend.successors![0].successors![0].$TYPE).toBe("ExportCreator");
    expect(frontend.successors![0].successors![0].creator_id).toBe("e1");
  });
});

describe("appendChildAtPath", () => {
  it("appends a child to root's successors when parentPath is 'root'", () => {
    const tree = makeNode("Root", "root", [makeNode("A", "a")]);
    const child = makeNode("B", "b");
    const result = appendChildAtPath(tree, "root", child);
    expect(result.successors!.length).toBe(2);
    expect(result.successors![0].creator_id).toBe("a");
    expect(result.successors![1].creator_id).toBe("b");
  });

  it("appends a child to a nested node's successors", () => {
    const tree = makeNode("Root", "root", [
      makeNode("A", "a", [makeNode("A1", "a1")]),
      makeNode("B", "b"),
    ]);
    const child = makeNode("A2", "a2");
    const result = appendChildAtPath(tree, "root.0", child);
    expect(result.successors![0].successors!.length).toBe(2);
    expect(result.successors![0].successors![0].creator_id).toBe("a1");
    expect(result.successors![0].successors![1].creator_id).toBe("a2");
    // Other siblings unchanged
    expect(result.successors![1].creator_id).toBe("b");
  });

  it("appends a child to a deeply nested node", () => {
    const tree = makeNode("Root", "root", [
      makeNode("A", "a", [
        makeNode("A1", "a1", [makeNode("A1a", "a1a")]),
      ]),
    ]);
    const child = makeNode("A1b", "a1b");
    const result = appendChildAtPath(tree, "root.0.0", child);
    expect(result.successors![0].successors![0].successors!.length).toBe(2);
    expect(result.successors![0].successors![0].successors![1].creator_id).toBe("a1b");
  });

  it("appends to a leaf node (creates successors array)", () => {
    const tree = makeNode("Root", "root", [makeNode("A", "a")]);
    const child = makeNode("A1", "a1");
    const result = appendChildAtPath(tree, "root.0", child);
    expect(result.successors![0].successors!.length).toBe(1);
    expect(result.successors![0].successors![0].creator_id).toBe("a1");
  });

  it("does not mutate the original tree", () => {
    const tree = makeNode("Root", "root", [makeNode("A", "a")]);
    const child = makeNode("B", "b");
    appendChildAtPath(tree, "root", child);
    expect(tree.successors!.length).toBe(1);
  });
});

describe("round-trip conversion", () => {
  it("frontend → backend → frontend preserves all data", () => {
    const original: PlanStepNode = {
      $TYPE: "ConstructionRootNode",
      creator_id: "root",
      successors: [
        {
          $TYPE: "WingLoftCreator",
          creator_id: "w1",
          offset: 0,
          wing_index: "main",
          wing_side: "BOTH",
          successors: [
            { $TYPE: "ExportCreator", creator_id: "e1", format: "step", successors: [] },
          ],
        },
      ],
    };
    const roundTripped = fromBackendTree(toBackendTree(original));
    expect(roundTripped.$TYPE).toBe("ConstructionRootNode");
    expect(roundTripped.creator_id).toBe("root");
    expect(roundTripped.successors!.length).toBe(1);

    const child = roundTripped.successors![0];
    expect(child.$TYPE).toBe("WingLoftCreator");
    expect(child.creator_id).toBe("w1");
    expect(child.offset).toBe(0);
    expect(child.wing_index).toBe("main");
    expect(child.wing_side).toBe("BOTH");

    const nested = child.successors![0];
    expect(nested.$TYPE).toBe("ExportCreator");
    expect(nested.creator_id).toBe("e1");
    expect(nested.format).toBe("step");
  });

  it("backend → frontend → backend preserves structure", () => {
    const backend = {
      $TYPE: "ConstructionRootNode",
      creator_id: "root",
      loglevel: 50,
      successors: {
        w1: {
          $TYPE: "ConstructionStepNode",
          creator_id: "w1",
          loglevel: 50,
          creator: { $TYPE: "WingLoftCreator", creator_id: "w1", loglevel: 10, offset: 5 },
          successors: {},
        },
      },
    };
    const roundTripped = toBackendTree(fromBackendTree(backend));
    expect(roundTripped.$TYPE).toBe("ConstructionRootNode");
    expect(roundTripped.loglevel).toBe(50);

    const step = (roundTripped.successors as Record<string, Record<string, unknown>>)["w1"];
    expect(step.$TYPE).toBe("ConstructionStepNode");
    expect(step.loglevel).toBe(50);

    const creator = step.creator as Record<string, unknown>;
    expect(creator.$TYPE).toBe("WingLoftCreator");
    expect(creator.loglevel).toBe(10);
    expect(creator.offset).toBe(5);
  });
});
