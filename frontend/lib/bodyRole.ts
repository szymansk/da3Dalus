/**
 * Role and attachment of a fuselage body (gh-1355, geometry format 7.6).
 *
 * What a body is (`role`) and the body it sits on (`attached_to`) are stated by the user or the
 * importer, never guessed from a name. The backend refuses an attachment to an unknown body, to
 * itself or in a cycle, a canopy without a parent, and a canopy outside its parent's x range.
 */

export type BodyRole = "fuselage" | "canopy" | "nacelle" | "fairing" | "pod" | "other";

export const BODY_ROLES: readonly BodyRole[] = [
  "fuselage",
  "canopy",
  "nacelle",
  "fairing",
  "pod",
  "other",
];

export const BODY_ROLE_LABELS: Record<BodyRole, string> = {
  fuselage: "Fuselage",
  canopy: "Canopy",
  nacelle: "Nacelle",
  fairing: "Fairing",
  pod: "Pod",
  other: "Other",
};

/** Glyph per role for the component tree, in the style of the control-surface role icons. */
export const BODY_ROLE_ICONS: Record<BodyRole, string> = {
  fuselage: "⬭", // horizontal ellipse
  canopy: "◠", // upper half circle
  nacelle: "◎", // bullseye
  fairing: "◖", // left half disc
  pod: "⬮", // vertical ellipse
  other: "○", // circle
};

/** A canopy is drawn semi-transparent so the body it sits on shows through. */
export const CANOPY_OPACITY = 0.35;

/** What the role and attachment rules read of one body. */
export interface BodyRelation {
  name: string;
  role?: BodyRole | null;
  attached_to?: string | null;
}

/** The fields of a body that a full-fuselage save must send back unchanged. */
export interface BodyFields {
  role: BodyRole;
  attached_to: string | null;
  symmetric: boolean;
}

/** The body's role; a body without one is a fuselage, the format's default. */
export function bodyRole(body: Pick<BodyRelation, "role"> | null | undefined): BodyRole {
  return body?.role ?? "fuselage";
}

/** The fields a new body starts with: a fuselage on nothing, not mirrored. */
export const NEW_BODY: BodyFields = { role: "fuselage", attached_to: null, symmetric: false };

/** The body fields of a loaded fuselage, so a save of its sections keeps them. */
export function bodyFields(
  body: (Pick<BodyRelation, "role" | "attached_to"> & { symmetric?: boolean }) | null | undefined,
): BodyFields {
  return {
    role: bodyRole(body),
    attached_to: body?.attached_to ?? null,
    symmetric: body?.symmetric ?? false,
  };
}

/** Whether attaching `name` to `parent` would close a cycle (the parent's chain leads to `name`). */
function closesCycle(name: string, parent: string, bodies: readonly BodyRelation[]): boolean {
  const byName = new Map(bodies.map((b) => [b.name, b]));
  const seen = new Set<string>();
  let current: string | null | undefined = parent;
  while (current != null && !seen.has(current)) {
    if (current === name) return true;
    seen.add(current);
    current = byName.get(current)?.attached_to;
  }
  return false;
}

/** The bodies `name` may be attached to: every other body whose chain does not lead back to it. */
export function attachableBodies(name: string, bodies: readonly BodyRelation[]): string[] {
  return bodies
    .filter((b) => b.name !== name && !closesCycle(name, b.name, bodies))
    .map((b) => b.name);
}

/** A body in tree order with its nesting depth below the aeroplane's body list. */
export interface BodyTreeEntry {
  name: string;
  depth: number;
}

/**
 * Order the bodies for the component tree: every body directly after the body it is attached to,
 * one level deeper. A body whose parent is not loaded (yet) stays at the top level, in list order.
 */
export function bodyTreeOrder(names: readonly string[], bodies: readonly BodyRelation[]): BodyTreeEntry[] {
  const parentOf = new Map(bodies.map((b) => [b.name, b.attached_to ?? null]));
  const known = new Set(names);
  const children = new Map<string, string[]>();
  const roots: string[] = [];
  for (const name of names) {
    const parent = parentOf.get(name) ?? null;
    if (parent != null && parent !== name && known.has(parent)) {
      children.set(parent, [...(children.get(parent) ?? []), name]);
    } else {
      roots.push(name);
    }
  }
  const order: BodyTreeEntry[] = [];
  const placed = new Set<string>();
  const visit = (name: string, depth: number) => {
    if (placed.has(name)) return;
    placed.add(name);
    order.push({ name, depth });
    for (const child of children.get(name) ?? []) visit(child, depth + 1);
  };
  for (const root of roots) visit(root, 0);
  // bodies in a cycle have no root; the backend refuses cycles, list them flat all the same
  for (const name of names) visit(name, 0);
  return order;
}
