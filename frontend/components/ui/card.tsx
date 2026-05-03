import { clsx } from "clsx";
import type { ReactNode } from "react";

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={clsx("glass rounded-xl p-5 transition hover:shadow-glow", className)}>{children}</section>;
}
