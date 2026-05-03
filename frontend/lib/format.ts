export function money(value: unknown) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "n/a";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

export function number(value: unknown, digits = 0) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "n/a";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(n);
}

export function score(value: unknown) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(1) : "n/a";
}

export function text(value: unknown) {
  if (Array.isArray(value)) return value.join(", ");
  if (value === null || value === undefined || value === "") return "n/a";
  return String(value);
}

export function loopId(row: Record<string, unknown>) {
  return text(row.loop_id ?? row.id ?? row.cycle_id ?? row.component_id);
}

