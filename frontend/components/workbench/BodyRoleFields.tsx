"use client";

import {
  BODY_ROLES,
  BODY_ROLE_LABELS,
  attachableBodies,
  needsParent,
  type BodyRelation,
  type BodyRole,
} from "@/lib/bodyRole";

const SELECT_CLASS =
  "rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground";

/**
 * Role and attachment of a fuselage body (gh-1355): what the body is and the body it sits on.
 * The parent list offers every other body of the aeroplane that does not sit on this one and
 * whose role the backend accepts as the parent of this role (gh-1375).
 */

const PARENT_NOTES: Partial<Record<BodyRole, string>> = {
  canopy: "A canopy needs the body it sits on.",
  spinner: "A spinner needs the body that carries the motor.",
};
export function BodyRoleFields({
  name,
  role,
  attachedTo,
  bodies,
  onChange,
  idPrefix = "body",
}: Readonly<{
  name: string;
  role: BodyRole;
  attachedTo: string | null;
  bodies: readonly BodyRelation[];
  onChange: (role: BodyRole, attachedTo: string | null) => void;
  idPrefix?: string;
}>) {
  const parents = attachableBodies(name, bodies, role);
  // a stored parent that is no longer offered (e.g. still loading) stays selectable
  const options = attachedTo && !parents.includes(attachedTo) ? [attachedTo, ...parents] : parents;
  const roleId = `${idPrefix}-role`;
  const parentId = `${idPrefix}-attached-to`;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex gap-3">
        <div className="flex flex-1 flex-col gap-1">
          <label htmlFor={roleId} className="text-[11px] text-muted-foreground">
            Role
          </label>
          <select
            id={roleId}
            value={role}
            onChange={(e) => onChange(e.target.value as BodyRole, attachedTo)}
            className={SELECT_CLASS}
          >
            {BODY_ROLES.map((r) => (
              <option key={r} value={r}>
                {BODY_ROLE_LABELS[r]}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-1 flex-col gap-1">
          <label htmlFor={parentId} className="text-[11px] text-muted-foreground">
            Attached to
          </label>
          <select
            id={parentId}
            value={attachedTo ?? ""}
            onChange={(e) => onChange(role, e.target.value === "" ? null : e.target.value)}
            className={SELECT_CLASS}
          >
            <option value="">(none)</option>
            {options.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
      </div>
      {needsParent(role) && attachedTo === null && (
        <p role="note" className="text-[11px] text-amber-400">
          {PARENT_NOTES[role]}
        </p>
      )}
    </div>
  );
}
