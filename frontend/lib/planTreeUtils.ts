import type { PlanStepNode } from "@/components/workbench/PlanTree";
import type { CreatorInfo } from "@/hooks/useCreators";

/** Navigate the plan tree to find the node at the given dot-separated path. */
export function getStepAtPath(tree: PlanStepNode, path: string): PlanStepNode | null {
  if (path === "root") return tree;
  const parts = path.replace("root.", "").split(".");
  let current: PlanStepNode = tree;
  for (const part of parts) {
    const idx = Number.parseInt(part, 10);
    if (!current.successors || !current.successors[idx]) return null;
    current = current.successors[idx];
  }
  return current;
}

/** Return a new tree with the node at `path` removed. */
export function deleteStepAtPath(tree: PlanStepNode, path: string): PlanStepNode {
  if (path === "root") return { ...tree, successors: [] };
  const parts = path.replace("root.", "").split(".");
  const lastIdx = Number.parseInt(parts[parts.length - 1], 10);
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
  const insertIdx = Number.parseInt(parts[parts.length - 1], 10) + 1;
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
        keys.push(out.key.replace(/\{id\}/g, stepId));
      }
    } else {
      keys.push(stepId);
    }
  }
  return keys;
}

/** Resolve `{param}` placeholders in an ID template using the given params. */
export function resolveIdTemplate(template: string, params: Record<string, unknown>): string {
  return template.replace(/\{(\w+)\}/g, (match, key) => {
    const val = params[key];
    return val != null && val !== "" ? String(val) : match;
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

  const fromIdx = Number.parseInt(fromParts[fromParts.length - 1], 10);
  const toIdx = Number.parseInt(toParts[toParts.length - 1], 10);
  if (fromIdx < toIdx) {
    const adjusted = [...toParts];
    adjusted[adjusted.length - 1] = String(toIdx - 1);
    return "root." + adjusted.join(".");
  }
  return toPath;
}
