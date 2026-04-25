import type { PlanStepNode } from "@/components/workbench/PlanTree";
import type { CreatorInfo } from "@/hooks/useCreators";
import { isShapeRefType } from "@/lib/planTreeUtils";

export interface ValidationIssue {
  path: string;
  creatorId: string;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  issues: ValidationIssue[];
}

function isEmpty(v: unknown): boolean {
  if (v == null) return true;
  if (typeof v === "string" && v.trim() === "") return true;
  return false;
}

function validateNode(
  node: PlanStepNode,
  path: string,
  availableShapes: Set<string>,
  creators: CreatorInfo[],
  issues: ValidationIssue[],
): void {
  const info = creators.find((c) => c.class_name === node.$TYPE);
  if (!info) {
    issues.push({
      path,
      creatorId: node.creator_id,
      message: `Unknown creator type "${node.$TYPE}"`,
    });
    return;
  }

  // Check required parameters
  for (const param of info.parameters) {
    const val = (node as Record<string, unknown>)[param.name];
    if (param.required && isEmpty(val)) {
      issues.push({
        path,
        creatorId: node.creator_id,
        message: `Missing required parameter "${param.name}"`,
      });
      continue;
    }
    // Check shape references (ShapeId or list[ShapeId])
    if (isShapeRefType(param.type) && !isEmpty(val)) {
      const refs = Array.isArray(val) ? val.map(String) : [String(val)];
      for (const ref of refs) {
        if (ref.trim() && !availableShapes.has(ref)) {
          issues.push({
            path,
            creatorId: node.creator_id,
            message: `Shape reference "${ref}" (${param.name}) is not available at this point`,
          });
        }
      }
    }
  }

  // Add this node's outputs to the available set, then walk successors.
  // Substitute all {placeholder} values with node properties.
  const stepId = node.creator_id;
  const nodeRecord = node as Record<string, unknown>;
  const resolveKey = (key: string): string => {
    let resolved = key.replaceAll("{id}", stepId);
    resolved = resolved.replace(/\{(\w+)\}/g, (_match, param) => {
      const val = nodeRecord[param];
      return typeof val === "string" ? val : typeof val === "number" ? String(val) : `{${param}}`;
    });
    return resolved;
  };
  const ownOutputs = info.outputs.length
    ? info.outputs.map((o) => resolveKey(o.key))
    : [stepId];
  const nextAvailable = new Set([...availableShapes, ...ownOutputs]);
  (node.successors ?? []).forEach((s, i) => {
    validateNode(s, `${path}.${i}`, nextAvailable, creators, issues);
  });
}

export function validatePlan(
  tree: PlanStepNode | null,
  creators: CreatorInfo[],
): ValidationResult {
  const issues: ValidationIssue[] = [];
  if (!tree) {
    return { valid: true, issues };
  }
  // Root has no creator (it's a wrapper); just walk successors
  const initialShapes = new Set<string>();
  (tree.successors ?? []).forEach((s, i) => {
    validateNode(s, `root.${i}`, initialShapes, creators, issues);
  });
  return { valid: issues.length === 0, issues };
}
