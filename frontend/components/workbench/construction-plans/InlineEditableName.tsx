"use client";

import { useState, useEffect, useRef } from "react";

interface InlineEditableNameProps {
  value: string;
  editing: boolean;
  onCommit: (newValue: string) => Promise<void> | void;
  onCancel: () => void;
  className?: string;
}

export function InlineEditableName({
  value,
  editing,
  onCommit,
  onCancel,
  className,
}: Readonly<InlineEditableNameProps>) {
  const [draft, setDraft] = useState(value);
  const [prevEditing, setPrevEditing] = useState(editing);
  const inputRef = useRef<HTMLInputElement>(null);

  // Sync draft from value when entering edit mode. Doing this during render
  // (instead of in useEffect) is the React 19 recommended pattern for
  // "adjust state when a prop changes" — see react-hooks/set-state-in-effect.
  if (editing !== prevEditing) {
    setPrevEditing(editing);
    if (editing) setDraft(value);
  }

  useEffect(() => {
    if (editing) {
      requestAnimationFrame(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      });
    }
  }, [editing]);

  if (!editing) {
    return <span className={className}>{value}</span>;
  }

  const commit = async () => {
    const trimmed = draft.trim();
    if (!trimmed || trimmed === value) {
      onCancel();
      return;
    }
    await onCommit(trimmed);
  };

  return (
    <input
      ref={inputRef}
      type="text"
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          commit();
        } else if (e.key === "Escape") {
          e.preventDefault();
          onCancel();
        }
      }}
      onClick={(e) => e.stopPropagation()}
      className={`rounded border border-primary bg-input px-1 outline-none ${className ?? ""}`}
    />
  );
}
