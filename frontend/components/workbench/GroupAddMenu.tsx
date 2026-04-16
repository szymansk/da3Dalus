"use client";

import { useEffect } from "react";
import { FolderPlus, Package, Box } from "lucide-react";

interface GroupAddMenuProps {
  groupName: string;
  /**
   * Action handlers are responsible for dismissing/transitioning the menu
   * themselves — picking an action does NOT auto-call onClose. onClose is
   * only invoked on outside click / escape key / explicit close button,
   * never as a consequence of an action pick.
   */
  onNewGroup: () => void;
  onAssignCots: () => void;
  onAssignConstructionPart: () => void;
  onClose: () => void;
  /**
   * Enables the "Assign Construction Part" option. Until gh#57-wvg lands
   * the Construction-Parts picker is not implemented, so the caller sets
   * this to false and the option renders as disabled.
   */
  constructionPartsEnabled?: boolean;
}

interface MenuItemProps {
  icon: React.ReactNode;
  label: string;
  hint?: string;
  disabled?: boolean;
  onClick: () => void;
}

function MenuItem({ icon, label, hint, disabled, onClick }: MenuItemProps) {
  return (
    <button
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] ${
        disabled
          ? "cursor-not-allowed opacity-40 text-foreground"
          : "text-foreground hover:bg-sidebar-accent"
      }`}
    >
      <span className="flex size-4 shrink-0 items-center justify-center text-muted-foreground">
        {icon}
      </span>
      <span className="flex-1 truncate">{label}</span>
      {hint && (
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-subtle-foreground">
          {hint}
        </span>
      )}
    </button>
  );
}

export function GroupAddMenu({
  groupName,
  onNewGroup,
  onAssignCots,
  onAssignConstructionPart,
  onClose,
  constructionPartsEnabled = false,
}: GroupAddMenuProps) {
  // Picking an action does not also close the menu — the parent is
  // expected to transition state, which implicitly unmounts this menu.
  // The menu closes on Escape via this effect.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      className="flex w-64 flex-col gap-0.5 rounded-xl border border-border bg-card p-1.5 shadow-2xl"
      onClick={(e) => e.stopPropagation()}
      role="menu"
    >
      <div className="px-2.5 pb-1 pt-1">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
          Add to &lsquo;{groupName}&rsquo;
        </span>
      </div>
      <div className="my-0.5 h-px w-full bg-border" />
      <MenuItem
        icon={<FolderPlus size={14} />}
        label="New Group"
        hint="inline"
        onClick={onNewGroup}
      />
      <MenuItem
        icon={<Package size={14} />}
        label="Assign COTS Component"
        hint="picker"
        onClick={onAssignCots}
      />
      <MenuItem
        icon={<Box size={14} />}
        label="Assign Construction Part"
        hint={constructionPartsEnabled ? "picker" : "soon"}
        disabled={!constructionPartsEnabled}
        onClick={onAssignConstructionPart}
      />
    </div>
  );
}
