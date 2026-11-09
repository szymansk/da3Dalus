/**
 * Role and attachment of a fuselage body (gh-1355): tree order, attachable parents, defaults.
 */
import { describe, it, expect } from "vitest";
import {
  BODY_ROLES,
  BODY_ROLE_ICONS,
  BODY_ROLE_LABELS,
  attachableBodies,
  needsParent,
  bodyFields,
  bodyRole,
  bodyTreeOrder,
  type BodyRelation,
} from "@/lib/bodyRole";

const BODIES: BodyRelation[] = [
  { name: "Haube", role: "canopy", attached_to: "Rumpf" },
  { name: "Rumpf", role: "fuselage", attached_to: null },
  { name: "Gondel", role: "nacelle", attached_to: null },
  { name: "Verkleidung", role: "fairing", attached_to: "Gondel" },
];

describe("bodyRole", () => {
  it("is the format's default fuselage for a body without role", () => {
    expect(bodyRole({})).toBe("fuselage");
    expect(bodyRole(null)).toBe("fuselage");
    expect(bodyRole({ role: "pod" })).toBe("pod");
  });

  it("has its own icon for every role", () => {
    const icons = BODY_ROLES.map((r) => BODY_ROLE_ICONS[r]);
    expect(new Set(icons).size).toBe(BODY_ROLES.length);
  });

  it("keeps role, attached_to and symmetric of a loaded body", () => {
    expect(bodyFields({ role: "canopy", attached_to: "Rumpf", symmetric: true })).toEqual({
      role: "canopy",
      attached_to: "Rumpf",
      symmetric: true,
    });
    expect(bodyFields(undefined)).toEqual({ role: "fuselage", attached_to: null, symmetric: false });
  });
});

describe("bodyTreeOrder", () => {
  it("lists every body under the body it is attached to", () => {
    const names = BODIES.map((b) => b.name);
    expect(bodyTreeOrder(names, BODIES)).toEqual([
      { name: "Rumpf", depth: 0 },
      { name: "Haube", depth: 1 },
      { name: "Gondel", depth: 0 },
      { name: "Verkleidung", depth: 1 },
    ]);
  });

  it("keeps a body whose parent is not loaded at the top level", () => {
    expect(bodyTreeOrder(["Haube", "Rumpf"], [])).toEqual([
      { name: "Haube", depth: 0 },
      { name: "Rumpf", depth: 0 },
    ]);
  });

  it("still lists bodies of a cycle, once each", () => {
    const cycle: BodyRelation[] = [
      { name: "a", attached_to: "b" },
      { name: "b", attached_to: "a" },
    ];
    expect(bodyTreeOrder(["a", "b"], cycle).map((e) => e.name)).toEqual(["a", "b"]);
  });
});

describe("attachableBodies", () => {
  it("offers every other body that does not sit on this one", () => {
    expect(attachableBodies("Rumpf", BODIES)).toEqual(["Gondel", "Verkleidung"]);
    expect(attachableBodies("Haube", BODIES)).toEqual(["Rumpf", "Gondel", "Verkleidung"]);
  });

  it("offers every body to a new one", () => {
    expect(attachableBodies("New body", BODIES)).toEqual(BODIES.map((b) => b.name));
  });
});

describe("spinner role (gh-1375)", () => {
  const WITH_SPINNER: BodyRelation[] = [
    ...BODIES,
    { name: "Spinner", role: "spinner", attached_to: "Rumpf" },
  ];

  it("is a selectable role with an English label", () => {
    expect(BODY_ROLES).toContain("spinner");
    expect(BODY_ROLE_LABELS.spinner).toBe("Spinner");
  });

  it("needs a parent, as a canopy does", () => {
    expect(needsParent("spinner")).toBe(true);
    expect(needsParent("canopy")).toBe(true);
    expect(needsParent("nacelle")).toBe(false);
  });

  it("is listed under the body that carries the motor", () => {
    const names = WITH_SPINNER.map((b) => b.name);
    expect(bodyTreeOrder(names, WITH_SPINNER).slice(0, 3)).toEqual([
      { name: "Rumpf", depth: 0 },
      { name: "Haube", depth: 1 },
      { name: "Spinner", depth: 1 },
    ]);
  });

  it("is offered no canopy and no spinner as its parent", () => {
    expect(attachableBodies("New spinner", WITH_SPINNER, "spinner")).toEqual([
      "Rumpf",
      "Gondel",
      "Verkleidung",
    ]);
  });

  it("offers a canopy no canopy as its parent, and other roles every body", () => {
    expect(attachableBodies("New canopy", WITH_SPINNER, "canopy")).toEqual([
      "Rumpf",
      "Gondel",
      "Verkleidung",
      "Spinner",
    ]);
    expect(attachableBodies("New pod", WITH_SPINNER, "pod")).toEqual(WITH_SPINNER.map((b) => b.name));
  });
});
