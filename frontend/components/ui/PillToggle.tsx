import type { LucideIcon } from "lucide-react";

export interface PillToggleOption<T extends string> {
  value: T;
  label: string;
  icon: LucideIcon;
}

interface PillToggleProps<T extends string> {
  options: PillToggleOption<T>[];
  value: T;
  onChange: (value: T) => void;
  isActive?: (optionValue: T, currentValue: T) => boolean;
}

export function PillToggle<T extends string>({
  options,
  value,
  onChange,
  isActive,
}: Readonly<PillToggleProps<T>>) {
  const check = isActive ?? ((opt: T, cur: T) => opt === cur);

  return (
    <div role="radiogroup" className="flex items-center gap-1 rounded-full border border-border bg-card p-1">
      {options.map((opt) => {
        const active = check(opt.value, value);
        const Icon = opt.icon;
        return (
          <button
            key={opt.value}
            role="radio"
            aria-checked={active}
            onClick={() => onChange(opt.value)}
            className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[12px] transition-colors ${
              active
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon size={12} />
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
