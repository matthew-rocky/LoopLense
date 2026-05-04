"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Bot, FileText, GitBranch, Link2, Route, ShieldAlert, X } from "lucide-react";
import type { AnyRow, NetworkGraph } from "@/lib/types";
import { money, score, text } from "@/lib/format";

type GraphNode = NetworkGraph["nodes"][number];
type GraphEdge = NetworkGraph["edges"][number];
type Selection =
  | { type: "node"; item: GraphNode }
  | { type: "edge"; item: GraphEdge }
  | null;

function location(node: GraphNode) {
  return [node.city, node.province].filter(Boolean).join(", ");
}

function hasValue(value: unknown) {
  return value !== null && value !== undefined && value !== "";
}

function meta(row: AnyRow | undefined, names: string[]) {
  if (!row) return undefined;
  for (const name of names) {
    if (hasValue(row[name])) return row[name];
  }
  return undefined;
}

function findNode(graph: NetworkGraph, id: string) {
  return graph.nodes.find((node) => node.id === id);
}

function connectedNames(graph: NetworkGraph, node: GraphNode) {
  const names = new Map<string, string>();
  graph.edges.forEach((edge) => {
    if (edge.source === node.id) names.set(edge.target, findNode(graph, edge.target)?.label ?? edge.target_name ?? edge.target);
    if (edge.target === node.id) names.set(edge.source, findNode(graph, edge.source)?.label ?? edge.source_name ?? edge.source);
  });
  return Array.from(names.values());
}

function edgeYear(edge: GraphEdge) {
  if (Array.isArray(edge.years) && edge.years.length === 1) return String(edge.years[0]);
  if (Array.isArray(edge.years) && edge.years.length > 1) return `${edge.years[0]}-${edge.years[edge.years.length - 1]}`;
  if (edge.min_year || edge.max_year) return `${text(edge.min_year)}-${text(edge.max_year)}`;
  return "n/a";
}

function evidenceRows(row: AnyRow | undefined, preferred: string[]) {
  if (!row) return [];
  const seen = new Set<string>();
  const rows: { label: string; value: unknown }[] = [];
  preferred.forEach((key) => {
    if (hasValue(row[key])) {
      seen.add(key);
      rows.push({ label: key.replaceAll("_", " "), value: row[key] });
    }
  });
  Object.entries(row).some(([key, value]) => {
    if (rows.length >= 7) return true;
    if (!seen.has(key) && hasValue(value) && typeof value !== "object") {
      rows.push({ label: key.replaceAll("_", " "), value });
    }
    return false;
  });
  return rows;
}

function loopContext(graph: NetworkGraph, edge: GraphEdge) {
  const path = graph.highlight_circular_path ?? [];
  const sourceIndex = path.indexOf(edge.source);
  const targetIndex = path.indexOf(edge.target);
  if (sourceIndex >= 0 && targetIndex >= 0) {
    return `${edge.source_name ?? edge.source} is position ${sourceIndex + 1}; ${edge.target_name ?? edge.target} is position ${targetIndex + 1} in the circular path.`;
  }
  if (edge.is_inferred) return "This inferred participant connector keeps the loop path readable where direct transfer evidence is incomplete.";
  return "This transfer is connected to the selected loop context.";
}

function whyEdgeMatters(edge: GraphEdge) {
  if (edge.is_cycle_edge) return "This edge is part of the circular flow, so changes to it affect the path LoopLens is investigating.";
  if (edge.is_inferred) return "This connector explains participant adjacency when the available transfer records do not contain a direct edge.";
  return "This transfer connects two organizations in the selected loop and contributes to the surrounding flow context.";
}

export function InvestigationPanel({
  selection,
  graph,
  onClose
}: {
  selection: Selection;
  graph?: NetworkGraph;
  onClose: () => void;
}) {
  return (
    <AnimatePresence>
      {selection && graph && (
        <motion.aside
          initial={{ opacity: 0, x: 26, scale: 0.985 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          exit={{ opacity: 0, x: 26, scale: 0.985 }}
          transition={{ duration: 0.24, ease: "easeOut" }}
          className="network-investigation-panel pointer-events-auto absolute right-4 top-4 z-40 flex max-h-[calc(100%-6.75rem)] w-[min(410px,calc(100%-2rem))] flex-col overflow-hidden rounded-2xl border p-0 shadow-glow backdrop-blur-xl"
        >
          <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-3">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--accent)]">Investigation Panel</div>
              <h2 className="mt-1 text-base font-bold">{selection.type === "node" ? "Organization" : "Transfer Edge"}</h2>
            </div>
            <button className="grid h-8 w-8 place-items-center rounded-lg border border-[var(--border)] transition hover:bg-[var(--surface-muted)]" onClick={onClose} title="Close panel">
              <X size={15} />
            </button>
          </div>
          <div className="table-scroll min-h-0 overflow-auto p-4">
            {selection.type === "node" ? <NodePanel node={selection.item} graph={graph} onClear={onClose} /> : <EdgePanel edge={selection.item} graph={graph} onClear={onClose} />}
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

function NodePanel({ node, graph, onClear }: { node: GraphNode; graph: NetworkGraph; onClear: () => void }) {
  const incoming = graph.edges.filter((edge) => edge.target === node.id);
  const outgoing = graph.edges.filter((edge) => edge.source === node.id);
  const connected = connectedNames(graph, node);
  const loc = location(node);
  const risk = meta(node.metadata, ["review_label", "risk_label", "priority", "label"]) ?? graph.summary?.label;
  const riskScore = meta(node.metadata, ["review_score", "score", "risk_score"]) ?? graph.summary?.score;
  return (
    <div className="space-y-4">
      <section>
        <div className="flex items-start gap-3">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-[var(--accent)]/30 bg-[var(--accent)]/12 text-[var(--accent)]">
            <ShieldAlert size={18} />
          </div>
          <div className="min-w-0">
            <h3 className="text-lg font-bold leading-6">{node.label}</h3>
            <p className="mt-1 text-xs text-[var(--muted)]">BN / registration: {text(node.bn ?? node.id)}</p>
            {loc && <p className="mt-1 text-sm text-[var(--muted)]">{loc}</p>}
          </div>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-2">
        <PanelMetric label="Total sent" value={money(node.total_sent)} />
        <PanelMetric label="Total received" value={money(node.total_received)} />
        <PanelMetric label="Outgoing" value={text(node.outgoing_edges)} />
        <PanelMetric label="Incoming" value={text(node.incoming_edges)} />
      </div>

      <section className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-3">
        <h4 className="text-sm font-semibold">Priority indicators</h4>
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
          <Info label="Priority" value={risk} compact />
          <Info label="Score" value={score(riskScore)} compact />
          <Info label="Cycle node" value={node.is_cycle_node ? "Yes" : "No"} compact />
          <Info label="Loop position" value={node.position_in_loop} compact />
        </div>
      </section>

      <Info label="Legal name" value={node.legal_name} />
      <Info label="Account name" value={node.account_name} />

      <section>
        <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold"><Link2 size={14} />Connected organizations</h4>
        <div className="flex flex-wrap gap-2">
          {connected.length === 0 && <EmptyLine>No connected organizations in this loop.</EmptyLine>}
          {connected.slice(0, 10).map((name) => (
            <span key={name} className="rounded-full border border-[var(--border)] bg-[var(--surface-muted)] px-2.5 py-1 text-xs font-medium">
              {name}
            </span>
          ))}
        </div>
      </section>

      <TransferList title="Outgoing transfers" edges={outgoing} direction="out" />
      <TransferList title="Incoming transfers" edges={incoming} direction="in" />
      <EvidenceMetadata row={node.metadata} preferred={["bn", "legal_name", "account_name", "city", "province", "review_label", "review_score", "position_in_loop"]} />
      <PanelActions loopId={graph.loop_id} onClear={onClear} />
    </div>
  );
}

function EdgePanel({ edge, graph, onClear }: { edge: GraphEdge; graph: NetworkGraph; onClear: () => void }) {
  return (
    <div className="space-y-4">
      <section>
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-[var(--accent)]/30 bg-[var(--accent)]/12 text-[var(--accent)]">
            <GitBranch size={18} />
          </div>
          <div className="min-w-0">
            <h3 className="truncate text-lg font-bold">{edge.source_name ?? edge.source}</h3>
            <p className="text-sm text-[var(--muted)]">transfers to</p>
            <h3 className="truncate text-lg font-bold">{edge.target_name ?? edge.target}</h3>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-2">
        <PanelMetric label="Amount" value={money(edge.amount)} />
        <PanelMetric label="Year" value={edgeYear(edge)} />
        <PanelMetric label="Edge count" value={text(edge.edge_count)} />
        <PanelMetric label="Evidence" value={edge.is_inferred ? "participant link" : text(edge.evidence_source)} />
      </div>

      <Info label="Sender organization" value={edge.source_name ?? edge.source} />
      <Info label="Receiver organization" value={edge.target_name ?? edge.target} />
      <Info label="Source / evidence metadata" value={edge.is_inferred ? "Inferred from loop participant linkage" : edge.evidence_source} />
      <Info label="Why this edge matters" value={whyEdgeMatters(edge)} />
      <Info label="Loop / path context" value={loopContext(graph, edge)} />
      <EvidenceMetadata row={edge.metadata} preferred={["evidence_source", "loop_id", "src", "dst", "from_bn", "to_bn", "total_amt", "amount", "year", "min_year", "max_year", "edge_count"]} />
      <PanelActions loopId={graph.loop_id} onClear={onClear} />
    </div>
  );
}

function TransferList({ title, edges, direction }: { title: string; edges: GraphEdge[]; direction: "in" | "out" }) {
  return (
    <section>
      <h4 className="mb-2 text-sm font-semibold">{title}</h4>
      <div className="space-y-2">
        {edges.length === 0 && <EmptyLine>No transfers in this direction.</EmptyLine>}
        {edges.slice(0, 8).map((edge, index) => (
          <div key={edge.id ?? `${edge.source}-${edge.target}-${index}`} className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-3 text-xs">
            <div className="font-semibold">{direction === "out" ? edge.target_name ?? edge.target : edge.source_name ?? edge.source}</div>
            <div className="mt-1 text-[var(--muted)]">{money(edge.amount)} - {edgeYear(edge)}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function EvidenceMetadata({ row, preferred }: { row?: AnyRow; preferred: string[] }) {
  const rows = evidenceRows(row, preferred);
  return (
    <section className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-3">
      <h4 className="text-sm font-semibold">Evidence metadata</h4>
      {rows.length === 0 ? (
        <p className="mt-2 text-xs leading-5 text-[var(--muted)]">No additional evidence metadata is available for this item.</p>
      ) : (
        <div className="mt-3 space-y-2">
          {rows.map((item) => <Info key={item.label} label={item.label} value={item.value} compact />)}
        </div>
      )}
    </section>
  );
}

function PanelActions({ loopId, onClear }: { loopId: string; onClear: () => void }) {
  return (
    <div className="grid gap-2 pt-1">
      <button className="network-panel-action" disabled title="Direct connections are highlighted while this item is selected">
        <Link2 size={15} />
        Connections highlighted
      </button>
      <a href={`/loops/detail?loop=${encodeURIComponent(loopId)}`} className="network-panel-action">
        <Route size={15} />
        Inspect path
      </a>
      <a href={`/memo?loop=${encodeURIComponent(loopId)}`} className="network-panel-action">
        <FileText size={15} />
        Generate memo
      </a>
      <a href={`/chat?loop=${encodeURIComponent(loopId)}`} className="network-panel-action">
        <Bot size={15} />
        Ask LoopLens
      </a>
      <button className="network-panel-action" onClick={onClear}>
        <X size={15} />
        Clear selection
      </button>
    </div>
  );
}

function PanelMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-3">
      <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">{label}</div>
      <div className="mt-1 truncate text-sm font-bold">{value}</div>
    </div>
  );
}

function Info({ label, value, compact = false }: { label: string; value: unknown; compact?: boolean }) {
  return (
    <div className={compact ? "rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2.5 py-2" : "rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-3"}>
      <div className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">{label}</div>
      <div className="mt-1 break-words text-sm">{text(value)}</div>
    </div>
  );
}

function EmptyLine({ children }: { children: string }) {
  return <div className="rounded-xl border border-dashed border-[var(--border)] bg-[var(--surface-muted)] p-3 text-xs text-[var(--muted)]">{children}</div>;
}
