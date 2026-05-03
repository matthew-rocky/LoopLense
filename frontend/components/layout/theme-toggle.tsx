"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "./theme-provider";

const options = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor }
] as const;

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  return (
    <div className="grid grid-cols-3 gap-1 rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] p-1">
      {options.map((option) => {
        const Icon = option.icon;
        const active = theme === option.value;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => setTheme(option.value)}
            title={option.label}
            className={`grid h-8 place-items-center rounded-md transition ${
              active ? "bg-[var(--accent)] text-[var(--accent-foreground)] shadow-sm" : "text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--foreground)]"
            }`}
          >
            <Icon size={15} />
          </button>
        );
      })}
    </div>
  );
}

