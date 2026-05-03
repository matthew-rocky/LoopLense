import type { LucideIcon } from "lucide-react";

export function EmptyState({ icon: Icon, title, description }: { icon: LucideIcon; title: string; description: string }) {
  return (
    <div className="grid place-items-center rounded-xl border border-dashed border-[var(--border)] bg-[var(--surface-muted)] p-10 text-center">
      <div className="grid h-12 w-12 place-items-center rounded-xl bg-[var(--surface)] text-[var(--accent)]">
        <Icon size={22} />
      </div>
      <h3 className="mt-4 text-lg font-semibold">{title}</h3>
      <p className="mt-2 max-w-md text-sm leading-6 text-[var(--muted)]">{description}</p>
    </div>
  );
}

