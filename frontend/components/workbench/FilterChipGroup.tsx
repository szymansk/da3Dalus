"use client";

/**
 * Shared multi-select chip-group primitive (gh-835).
 *
 * Renders a horizontal list of toggle chips.  Each chip is either active
 * (highlighted, contributes to OR-filter) or inactive (neutral).
 * Clicking an active chip removes it; clicking an inactive chip adds it.
 *
 * Used by AirfoilSuitabilityFilterBar for both family chips and role-tag chips.
 * Factor here prevents copy-paste of chip markup across filter dimensions.
 */

interface ChipOption<T extends string> {
  readonly value: T;
  readonly label: string;
  /** Optional tooltip description shown on hover. */
  readonly description?: string;
}

interface FilterChipGroupProps<T extends string> {
  /** All available options for this group. */
  readonly options: ReadonlyArray<ChipOption<T>>;
  /** Currently selected values (subset of options[].value). */
  readonly selected: T[];
  /** Called with the new selected array after a toggle. */
  readonly onChange: (next: T[]) => void;
  /** Accessible group label (visually hidden but read by screen readers). */
  readonly ariaLabel: string;
}

/**
 * Multi-select chip group.  OR logic: any active chip makes a match.
 * Selecting all chips is equivalent to selecting none (no filter).
 */
export function FilterChipGroup<T extends string>({
  options,
  selected,
  onChange,
  ariaLabel,
}: FilterChipGroupProps<T>) {
  function toggle(value: T) {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value));
    } else {
      onChange([...selected, value]);
    }
  }

  return (
    <div role="group" aria-label={ariaLabel} className="flex flex-wrap gap-1.5">
      {options.map((opt) => {
        const isActive = selected.includes(opt.value);
        return (
          <button
            key={opt.value}
            type="button"
            data-testid={`chip-${opt.value}`}
            aria-pressed={isActive}
            title={opt.description}
            onClick={() => toggle(opt.value)}
            className={`rounded-full border px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] transition-colors ${
              isActive
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-muted-foreground hover:border-primary/50 hover:text-foreground"
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
