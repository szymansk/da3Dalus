"use client";

import Link from "next/link";
import { useUnsavedChanges } from "@/components/workbench/UnsavedChangesContext";
import type { ComponentProps } from "react";

export function GuardedLink(props: ComponentProps<typeof Link>) {
  const { isDirty, requestNavigation } = useUnsavedChanges();
  const href = typeof props.href === "string" ? props.href : props.href.pathname ?? "/";

  return (
    <Link
      {...props}
      onClick={(e) => {
        if (isDirty) {
          e.preventDefault();
          requestNavigation(href);
        }
        props.onClick?.(e);
      }}
    />
  );
}
