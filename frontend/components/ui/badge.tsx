import { clsx } from "clsx";

export function Badge({ label }: { label: unknown }) {
  const text = String(label ?? "Unscored");
  const tone =
    text === "High"
      ? "border-amber-400/35 bg-amber-400/15 text-amber-500 dark:text-amber-100"
      : text === "Medium"
        ? "border-sky-400/35 bg-sky-400/15 text-sky-600 dark:text-sky-100"
        : "border-emerald-400/30 bg-emerald-400/12 text-emerald-600 dark:text-emerald-100";
  return <span className={clsx("rounded-full border px-2.5 py-1 text-xs font-semibold", tone)}>{text}</span>;
}
