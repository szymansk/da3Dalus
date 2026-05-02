import type { PlanStepNode } from "@/components/workbench/PlanTree";
import type { CreatorInfo } from "@/hooks/useCreators";

/**
 * Resolve a parameter value to a string.
 * Returns the value as-is if it is a string, converts numbers, or returns the fallback.
 */
export function resolveParamValue(val: unknown, fallback: string): string {
  if (typeof val === "string") return val;
  if (typeof val === "number") return String(val);
  return fallback;
}

/** Navigate the plan tree to find the node at the given dot-separated path. */
export function getStepAtPath(tree: PlanStepNode, path: string): PlanStepNode | null {
  if (path === "root") return tree;
  const parts = path.replace("root.", "").split(".");
  let current: PlanStepNode = tree;
  for (const part of parts) {
    const idx = Number.parseInt(part, 10);
    if (!current.successors?.[idx]) return null;
    current = current.successors[idx];
  }
  return current;
}

/** Return a new tree with the node at `path` removed. */
export function deleteStepAtPath(tree: PlanStepNode, path: string): PlanStepNode {
  if (path === "root") return { ...tree, successors: [] };
  const parts = path.replace("root.", "").split(".");
  const lastIdx = Number.parseInt(parts.at(-1)!, 10);
  const parentPath = parts.slice(0, -1);

  function navigate(node: PlanStepNode, remaining: string[]): PlanStepNode {
    if (remaining.length === 0) {
      const newSuccessors = [...(node.successors ?? [])];
      newSuccessors.splice(lastIdx, 1);
      return { ...node, successors: newSuccessors };
    }
    const idx = Number.parseInt(remaining[0], 10);
    const newSuccessors = [...(node.successors ?? [])];
    newSuccessors[idx] = navigate(newSuccessors[idx], remaining.slice(1));
    return { ...node, successors: newSuccessors };
  }

  return navigate(tree, parentPath);
}

/** Return a new tree with `step` inserted after the node at `path`. */
export function insertStepAtPath(
  tree: PlanStepNode,
  path: string,
  step: PlanStepNode,
): PlanStepNode {
  if (path === "root") {
    return { ...tree, successors: [...(tree.successors ?? []), step] };
  }
  const parts = path.replace("root.", "").split(".");
  const insertIdx = Number.parseInt(parts.at(-1)!, 10) + 1;
  const parentParts = parts.slice(0, -1);

  function navigate(node: PlanStepNode, remaining: string[]): PlanStepNode {
    if (remaining.length === 0) {
      const newSuccessors = [...(node.successors ?? [])];
      newSuccessors.splice(insertIdx, 0, step);
      return { ...node, successors: newSuccessors };
    }
    const idx = Number.parseInt(remaining[0], 10);
    const newSuccessors = [...(node.successors ?? [])];
    newSuccessors[idx] = navigate(newSuccessors[idx], remaining.slice(1));
    return { ...node, successors: newSuccessors };
  }

  return navigate(tree, parentParts);
}

/** Return a new tree with `updatedNode` placed at `path`. */
export function updateNodeAtPath(
  tree: PlanStepNode,
  path: string,
  updatedNode: PlanStepNode,
): PlanStepNode {
  if (path === "root") return updatedNode;
  const parts = path.replace("root.", "").split(".");
  const idx = Number.parseInt(parts[0], 10);
  const rest = parts.slice(1).join(".");
  const newSuccessors = [...(tree.successors ?? [])];
  newSuccessors[idx] = rest
    ? updateNodeAtPath(newSuccessors[idx], rest, updatedNode)
    : updatedNode;
  return { ...tree, successors: newSuccessors };
}

/**
 * Collect shape keys produced by all steps before `stopPath` in the tree.
 * Uses the creator list to resolve output key templates.
 */
export function collectAvailableShapeKeys(
  tree: PlanStepNode | null,
  creators: CreatorInfo[],
  stopPath?: string | null,
): string[] {
  if (!tree) return [];
  const keys: string[] = [];
  const successors = tree.successors ?? [];
  for (let i = 0; i < successors.length; i++) {
    const stepPath = `root.${i}`;
    if (stopPath && stepPath === stopPath) break;
    const step = successors[i];
    const stepId = step.creator_id ?? step.$TYPE ?? "step";
    const creator = creators.find(
      (c) => c.class_name === step.$TYPE || c.class_name === step.creator_id,
    );
    if (creator?.outputs.length) {
      for (const out of creator.outputs) {
        keys.push(out.key.replaceAll("{id}", stepId));
      }
    } else {
      keys.push(stepId);
    }
  }
  return keys;
}

/** Resolve `{param}` placeholders in an ID template using the given params. */
export function resolveIdTemplate(template: string, params: Record<string, unknown>): string {
  return template.replaceAll(/\{(\w+)\}/g, (match, key) => {
    const val = params[key as string];
    if (val == null || val === "") return match;
    if (typeof val === "string") return val;
    if (typeof val === "number" || typeof val === "boolean") return String(val);
    return JSON.stringify(val);
  });
}

/**
 * Compute the adjusted target path when reordering within the same parent.
 * After removing `fromPath`, indices shift down by 1 for later siblings.
 */
export function computeReorderTargetPath(fromPath: string, toPath: string): string {
  const fromParts = fromPath.replace("root.", "").split(".");
  const toParts = toPath.replace("root.", "").split(".");
  if (fromParts.length !== toParts.length) return toPath;

  const fromParent = fromParts.slice(0, -1).join(".");
  const toParent = toParts.slice(0, -1).join(".");
  if (fromParent !== toParent) return toPath;

  const fromIdx = Number.parseInt(fromParts.at(-1)!, 10);
  const toIdx = Number.parseInt(toParts.at(-1)!, 10);
  if (fromIdx < toIdx) {
    const adjusted = [...toParts];
    adjusted[adjusted.length - 1] = String(toIdx - 1);
    return "root." + adjusted.join(".");
  }
  return toPath;
}

/** Return a new tree with `child` appended to the successors of the node at `parentPath`. */
export function appendChildAtPath(
  tree: PlanStepNode,
  parentPath: string,
  child: PlanStepNode,
): PlanStepNode {
  if (parentPath === "root") {
    return { ...tree, successors: [...(tree.successors ?? []), child] };
  }
  const parts = parentPath.replace("root.", "").split(".");
  const idx = Number.parseInt(parts[0], 10);
  const rest = parts.slice(1);
  const newSuccessors = [...(tree.successors ?? [])];
  if (rest.length === 0) {
    const target = newSuccessors[idx];
    newSuccessors[idx] = { ...target, successors: [...(target.successors ?? []), child] };
  } else {
    newSuccessors[idx] = appendChildAtPath(newSuccessors[idx], "root." + rest.join("."), child);
  }
  return { ...tree, successors: newSuccessors };
}

/** Default loglevel matching Python's logging.FATAL (50). */
const DEFAULT_LOGLEVEL = 50;

/**
 * Convert the frontend's simplified plan tree (array-based successors,
 * creators as direct nodes) to the backend's GeneralJSONEncoder format
 * (dict-keyed successors, ConstructionStepNode wrappers around creators).
 */
export function toBackendTree(
  node: PlanStepNode,
): Record<string, unknown> {
  const successors = node.successors ?? [];
  const backendSuccessors: Record<string, Record<string, unknown>> = {};

  for (const child of successors) {
    // eslint-disable-next-line sonarjs/no-unused-vars -- destructure-to-exclude
    const { $TYPE, creator_id, successors: _childSuccessors, _creatorIdDirty: _dirty, ...creatorParams } = child;
    const loglevel = (creatorParams.loglevel as number) ?? DEFAULT_LOGLEVEL;
    // Remove loglevel from creatorParams to avoid duplication — it's set explicitly
    delete creatorParams.loglevel;

    if (backendSuccessors[creator_id] !== undefined) {
      console.warn(`Duplicate creator_id "${creator_id}" in plan tree — second entry overwrites the first`);
    }
    backendSuccessors[creator_id] = {
      $TYPE: "ConstructionStepNode",
      creator_id,
      loglevel: DEFAULT_LOGLEVEL,
      creator: {
        $TYPE,
        creator_id,
        loglevel,
        ...creatorParams,
      },
      successors: toBackendTree({ ...child, $TYPE: "tmp", creator_id: "tmp" }).successors as Record<string, unknown>,
    };
  }

  // eslint-disable-next-line sonarjs/no-unused-vars -- destructure-to-exclude
  const { successors: _s, _creatorIdDirty: _d, ...rootFields } = node as Record<string, unknown>;
  return {
    ...rootFields,
    // Root must always be ConstructionRootNode for the GeneralJSONDecoder
    $TYPE: "ConstructionRootNode",
    loglevel: (rootFields.loglevel as number) ?? DEFAULT_LOGLEVEL,
    successors: backendSuccessors,
  };
}

/**
 * Convert the backend's GeneralJSONEncoder format (dict-keyed successors,
 * ConstructionStepNode wrappers) to the frontend's simplified format
 * (array-based successors, creators as direct nodes).
 *
 * If the tree is already in frontend format (array successors), it is
 * returned as-is.
 */
export function fromBackendTree(
  tree: Record<string, unknown>,
): PlanStepNode {
  const rawSuccessors = tree.successors;

  // Already in frontend format (array) or missing
  if (!rawSuccessors || Array.isArray(rawSuccessors)) {
    const node = tree as unknown as PlanStepNode;
    // Still recurse into children to handle mixed formats
    if (Array.isArray(rawSuccessors) && rawSuccessors.length > 0) {
      return {
        ...node,
        successors: rawSuccessors.map((child) =>
          fromBackendTree(child as Record<string, unknown>),
        ),
      };
    }
    return node;
  }

  // Backend format: dict-keyed ConstructionStepNodes
  const dictSuccessors = rawSuccessors as Record<string, Record<string, unknown>>;
  const children: PlanStepNode[] = Object.values(dictSuccessors).map((stepNode) => {
    const creator = (stepNode.creator ?? {}) as Record<string, unknown>;
    const { $TYPE, creator_id, loglevel, ...params } = creator;
    const childSuccessors = stepNode.successors as Record<string, unknown> | undefined;

    // Recursively convert nested successors
    const converted = childSuccessors && Object.keys(childSuccessors).length > 0
      ? fromBackendTree({
          $TYPE: "tmp",
          creator_id: "tmp",
          successors: childSuccessors,
        }).successors
      : [];

    return {
      $TYPE: $TYPE as string,
      creator_id: creator_id as string,
      loglevel: loglevel as number,
      ...params,
      successors: converted ?? [],
    } as PlanStepNode;
  });

  // eslint-disable-next-line sonarjs/no-unused-vars -- destructure-to-exclude
  const { successors: _s, ...rootFields } = tree;
  return {
    ...(rootFields as unknown as PlanStepNode),
    successors: children,
  };
}

/** Build a unique creator_id from a base string, avoiding collisions with existing tree IDs. */
function uniqueCreatorId(tree: PlanStepNode, base: string): string {
  const existing = new Set<string>();
  function walk(n: PlanStepNode) {
    existing.add(n.creator_id);
    (n.successors ?? []).forEach(walk);
  }
  walk(tree);
  if (!existing.has(base)) return base;
  let i = 1;
  while (existing.has(`${base}_${i}`)) i++;
  return `${base}_${i}`;
}

/** Build a new PlanStepNode from CreatorInfo, with a unique creator_id and seeded defaults. */
export function buildStepNode(creator: CreatorInfo, tree: PlanStepNode): PlanStepNode {
  const base = creator.suggested_id ?? creator.class_name.replace(/Creator$/, "").toLowerCase();
  const node: PlanStepNode = {
    $TYPE: creator.class_name,
    creator_id: base, // placeholder — resolved after defaults are set
    loglevel: 50,
    successors: [],
  };
  for (const param of creator.parameters) {
    if (param.default != null) {
      (node as Record<string, unknown>)[param.name] = param.default;
    }
  }
  // Resolve {placeholder} in creator_id using the seeded default values
  const nodeRecord = node as Record<string, unknown>;
  node.creator_id = base.replace(/\{(\w+)\}/g, (_match, param) =>
    resolveParamValue(nodeRecord[param], `{${param}}`),
  );
  // Ensure uniqueness after resolution
  node.creator_id = uniqueCreatorId(tree, node.creator_id);
  return node;
}

export interface ResolvedShapeInput {
  paramName: string;
  boundValue: string | null;  // null = unbound (show in red)
}

export interface ResolvedShapes {
  inputs: ResolvedShapeInput[];
  outputs: string[];
}

/** Check if a CreatorParam type is a shape reference (ShapeId or list[ShapeId]). */
export function isShapeRefType(type: string): boolean {
  return type === "ShapeId" || type === "list[ShapeId]";
}

export function resolveNodeShapes(
  node: PlanStepNode,
  creators: CreatorInfo[],
): ResolvedShapes {
  const info = creators.find(c => c.class_name === node.$TYPE);
  if (!info) return { inputs: [], outputs: [] };
  const stepId = node.creator_id;

  const inputs: ResolvedShapeInput[] = [];
  for (const p of info.parameters) {
    if (!isShapeRefType(p.type)) continue;
    const val = (node as Record<string, unknown>)[p.name];
    if (p.type === "list[ShapeId]" && Array.isArray(val)) {
      // Multi-shape ref: each element is a separate input
      for (const v of val) {
        const bound = typeof v === "string" && v.trim() !== "" ? v : null;
        inputs.push({ paramName: p.name, boundValue: bound });
      }
      // If list is empty, show one unbound entry
      if (val.length === 0) {
        inputs.push({ paramName: p.name, boundValue: null });
      }
    } else {
      const bound = typeof val === "string" && val.trim() !== "" ? val : null;
      inputs.push({ paramName: p.name, boundValue: bound });
    }
  }

  // Resolve output key placeholders: {id} → creator_id, {param} → node[param]
  const nodeRecord = node as Record<string, unknown>;
  const resolveKey = (key: string): string => {
    let resolved = key.replaceAll("{id}", stepId);
    // Replace remaining {param_name} placeholders with actual values
    resolved = resolved.replace(/\{(\w+)\}/g, (_match, param) =>
      resolveParamValue(nodeRecord[param], `{${param}}`),
    );
    return resolved;
  };

  return {
    inputs,
    outputs: info.outputs.map(o => resolveKey(o.key)),
  };
}
