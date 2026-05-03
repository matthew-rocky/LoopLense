"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Bot, FileText, Loader2, Network, Pause, Play, Search, X, ExternalLink } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { getNetwork } from "@/lib/api";
import type { AnyRow, NetworkGraph } from "@/lib/types";
import { loopId, money, score, text } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { NetworkGraphView } from "./network-graph";

type GraphNode = NetworkGraph["nodes"][number];
type GraphEdge = NetworkGraph["edges"][number];
type Selection =
  | { type: "node"; item: GraphNode }
  | { type: "edge"; item: GraphEdge }
  | null;

function years(graph?: NetworkGraph) {
  const values = graph?.edges.flatMap((edge) => edge.years ?? []) ?? [];
  return Array.from(new Set(values)).sort((a, b) => a - b);
}

function findNode(graph: NetworkGraph | undefined, id: string) {
  return graph?.nodes.find((node) => node.id === id);
}

export function NetworkWorkspace({ initialLoopId, initialGraph, loopOptions }: { initialLoopId: string; initialGraph?: NetworkGraph; loopOptions: AnyRow[] }) {
  const [loop, setLoop] = useState(initialLoopId);
  const [graph, setGraph] = useState<NetworkGraph | undefined>(initialGraph);
  const [selected, setSelected] = useState<Selection>(null);
  const [year, setYear] = useState<number | "all">("all");
  const [playing, setPlaying] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const availableYears = useMemo(() => years(graph), [graph]);

  async function load(nextLoop = loop) {
    if (!nextLoop.trim()) return;
    setLoading(true);
    setError("");
    setSelected(null);
    setPlaying(false);
    try {
      const result = await getNetwork(nextLoop.trim());
      setGraph(result);
      setLoop(nextLoop.trim());
      setYear("all");
    } catch {
      setError("Could not load this loop network. Confirm the backend is running and the loop ID exists.");
    } finally {
      setLoading(false);
    }
  }

  const setManualYear = useCallback((nextYear: number | "all") => {
    setPlaying(false);
    setYear(nextYear);
  }, []);

  useEffect(() => {
    if (availableYears.length <= 1 && playing) {
      setPlaying(false);
    }
  }, [availableYears.length, playing]);

  useEffect(() => {
    if (!playing || availableYears.length <= 1) return;
    const id = window.setInterval(() => {
      setYear((current) => {
        if (current === "all") return availableYears[0];
        const index = availableYears.indexOf(current);
        const nextIndex = index < 0 ? 0 : index + 1;
        if (nextIndex >= availableYears.length) {
          window.clearInterval(id);
          setPlaying(false);
          return current;
        }
        const nextYear = availableYears[nextIndex];
        if (nextIndex === availableYears.length - 1) {
          window.clearInterval(id);
          setPlaying(false);
        }
        return nextYear;
      });
    }, 1000);
    return () => window.clearInterval(id);
  }, [playing, availableYears]);

  const togglePlaying = useCallback(() => {
    if (availableYears.length <= 1) return;
    setPlaying((current) => {
      if (current) return false;
      if (year === "all" || availableYears.indexOf(year) === availableYears.length - 1) {
        setYear(availableYears[0]);
      }
      return true;
    });
  }, [availableYears, year]);

  const handleSelect = useCallback((selection: Selection) => {
    setSelected(selection);
    if (selection) setPanelOpen(true);
  }, []);

  return (
    <div className="flex h-[calc(100vh-9rem)] min-h-[760px] flex-col overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)]">
      <div className="grid gap-3 border-b border-[var(--border)] bg-[var(--surface-strong)] p-4 xl:grid-cols-[1fr_auto_auto]">
        <label className="relative">
          <Search className="absolute left-3 top-3 text-[var(--muted)]" size={17} />
          <input
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] py-2.5 pl-10 pr-3 text-sm outline-none focus:focus-ring"
            value={loop}
            onChange={(event) => setLoop(event.target.value)}
            list="network-loop-options"
            placeholder="Enter or select loop ID"
          />
        </label>
        <datalist id="network-loop-options">
          {loopOptions.map((row) => <option key={loopId(row)} value={loopId(row)}>{Array.isArray(row.participant_names) ? row.participant_names.slice(0, 2).join(", ") : loopId(row)}</option>)}
        </datalist>
        <select className="rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2.5 text-sm outline-none focus:focus-ring" value={loop} onChange={(event) => load(event.target.value)}>
          {loopOptions.map((row) => <option key={loopId(row)} value={loopId(row)}>Loop {loopId(row)}</option>)}
        </select>
        <Button onClick={() => load()} disabled={loading}>
          {loading ? <Loader2 className="animate-spin" size={16} /> : <Network size={16} />}
          Load
        </Button>
      </div>

      {graph && <SummaryCards graph={graph} />}
      {error && <div className="mx-4 mt-4 rounded-xl border border-red-400/30 bg-red-400/10 p-3 text-sm text-[var(--danger)]">{error}</div>}

      <div className="grid min-h-0 flex-1 gap-4 p-4 xl:grid-cols-[1fr_auto]">
        <div className="relative min-h-0">
          {loading && (
            <div className="absolute inset-0 z-20 grid place-items-center rounded-2xl bg-[var(--surface)]/70 backdrop-blur">
              <div className="flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface-strong)] px-4 py-3 text-sm">
                <Loader2 className="animate-spin text-[var(--accent)]" size={18} />
                Building intelligence map...
              </div>
            </div>
          )}
          {graph && graph.nodes.length > 0 ? (
            <>
              <NetworkGraphView graph={graph} year={year} selected={selected} onSelect={handleSelect} focusMode={focusMode} onToggleFocus={() => setFocusMode((value) => !value)} />
              <YearControl year={year} setYear={setManualYear} years={availableYears} playing={playing} onTogglePlay={togglePlaying} />
            </>
          ) : (
            <EmptyState icon={Network} title="No network selected" description="Select a loop to inspect the circular transfer path with organization names and BN metadata." />
          )}
        </div>
        <AnimatePresence>
          {panelOpen && (
            <motion.aside
              initial={{ opacity: 0, x: 24 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 24 }}
              className="w-full overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface-strong)] xl:w-[390px]"
            >
              <div className="flex items-center justify-between border-b border-[var(--border)] p-4">
                <div>
                  <div className="text-xs uppercase tracking-wide text-[var(--muted)]">Investigation Panel</div>
                  <h2 className="font-semibold">{selected ? selected.type === "node" ? "Organization" : "Transfer Edge" : "No selection"}</h2>
                </div>
                <button className="rounded-lg border border-[var(--border)] p-2" onClick={() => setPanelOpen(false)} title="Collapse panel">
                  <X size={16} />
                </button>
              </div>
              <div className="max-h-[calc(100vh-18rem)] overflow-auto p-4 table-scroll">
                <SelectionPanel selection={selected} graph={graph} />
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function YearControl({ year, setYear, years, playing, onTogglePlay }: { year: number | "all"; setYear: (year: number | "all") => void; years: number[]; playing: boolean; onTogglePlay: () => void }) {
  if (years.length === 0) {
    return (
      <div className="pointer-events-auto absolute bottom-5 left-1/2 z-30 -translate-x-1/2 rounded-full border border-[var(--border)] bg-[var(--surface-strong)]/88 px-4 py-2 text-sm text-[var(--muted)] shadow-glow backdrop-blur">
        No year data
      </div>
    );
  }
  const selectedIndex = year === "all" ? 0 : Math.max(1, years.indexOf(year) + 1);
  const playDisabled = years.length <= 1;
  return (
    <div className="pointer-events-auto absolute bottom-5 left-1/2 z-30 flex max-w-[calc(100%-2rem)] -translate-x-1/2 flex-wrap items-center justify-center gap-3 rounded-2xl border border-[var(--border)] bg-[var(--surface-strong)]/88 px-3 py-2.5 shadow-glow backdrop-blur md:flex-nowrap md:px-4">
      <button
        className="grid h-9 w-9 place-items-center rounded-full border border-[var(--border)] bg-[var(--surface-muted)] text-[var(--accent)] transition hover:bg-[var(--surface)] disabled:cursor-not-allowed disabled:opacity-45"
        onClick={onTogglePlay}
        disabled={playDisabled}
        title={playing ? "Pause yearly transfer animation" : "Play yearly transfer animation"}
      >
        {playing ? <Pause size={16} /> : <Play size={16} />}
      </button>
      <select
        className="min-w-28 rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-2.5 py-2 text-sm font-semibold outline-none focus:focus-ring"
        value={year}
        onChange={(event) => setYear(event.target.value === "all" ? "all" : Number(event.target.value))}
        title="Select all years or a specific year"
      >
        <option value="all">All years</option>
        {years.map((item) => <option key={item} value={item}>{item}</option>)}
      </select>
      <div className="flex min-w-[220px] flex-1 items-center gap-2 md:min-w-[300px]">
        <span className="text-xs font-semibold text-[var(--muted)]">{years[0]}</span>
        <input
          className="min-w-36 flex-1 accent-[var(--accent)]"
          type="range"
          min={0}
          max={years.length}
          value={selectedIndex}
          onChange={(event) => {
            const index = Number(event.target.value);
            setYear(index === 0 ? "all" : years[index - 1]);
          }}
          title="Filter graph by year"
        />
        <span className="text-xs font-semibold text-[var(--muted)]">{years[years.length - 1]}</span>
      </div>
      <div className="min-w-16 rounded-full border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-1.5 text-center text-sm font-semibold">
        {year === "all" ? "All years" : year}
      </div>
    </div>
  );
}

function SummaryCards({ graph }: { graph: NetworkGraph }) {
  const summary = graph.summary ?? {};
  return (
    <div className="grid gap-3 border-b border-[var(--border)] bg-[var(--surface-muted)] p-4 md:grid-cols-3 xl:grid-cols-7">
      <Metric label="Loop" value={graph.loop_id} />
      <Metric label="Participants" value={text(summary.participant_count ?? graph.nodes.length)} />
      <Metric label="Circular Flow" value={money(summary.circular_flow)} />
      <Metric label="Highest Edge" value={money(summary.highest_transfer_edge)} />
      <Metric label="Score" value={score(summary.score)} />
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3"><div className="text-xs text-[var(--muted)]">Priority</div><div className="mt-2"><Badge label={summary.label} /></div></div>
      <Metric label="Years / Edges" value={`${text(summary.min_year)}-${text(summary.max_year)} / ${text(summary.total_edges)}`} />
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3">
      <div className="text-xs text-[var(--muted)]">{label}</div>
      <div className="mt-1 truncate font-semibold">{value}</div>
    </div>
  );
}

function SelectionPanel({ selection, graph }: { selection: Selection; graph?: NetworkGraph }) {
  if (!selection || !graph) {
    return <p className="text-sm leading-6 text-[var(--muted)]">Select a node or edge to inspect transfers, metadata, and investigation actions.</p>;
  }
  if (selection.type === "node") {
    const node = selection.item;
    const incoming = graph.edges.filter((edge) => edge.target === node.id);
    const outgoing = graph.edges.filter((edge) => edge.source === node.id);
    return (
      <div className="space-y-4">
        <div>
          <h3 className="text-lg font-bold">{node.label}</h3>
          <p className="mt-1 text-xs text-[var(--muted)]">{node.bn}</p>
          {[node.city, node.province].filter(Boolean).length > 0 && <p className="mt-1 text-sm text-[var(--muted)]">{[node.city, node.province].filter(Boolean).join(", ")}</p>}
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Metric label="Sent" value={money(node.total_sent)} />
          <Metric label="Received" value={money(node.total_received)} />
          <Metric label="Outgoing" value={text(node.outgoing_edges)} />
          <Metric label="Incoming" value={text(node.incoming_edges)} />
        </div>
        <Info label="Legal name" value={node.legal_name} />
        <Info label="Account name" value={node.account_name} />
        <Info label="Loop position" value={node.position_in_loop} />
        <TransferList title="Outgoing Transfers" edges={outgoing} direction="out" />
        <TransferList title="Incoming Transfers" edges={incoming} direction="in" />
        <Actions loopId={graph.loop_id} org={node.label} />
      </div>
    );
  }
  const edge = selection.item;
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-bold">{edge.source_name}</h3>
        <p className="text-sm text-[var(--muted)]">transfers to</p>
        <h3 className="text-lg font-bold">{edge.target_name}</h3>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Metric label="Amount" value={money(edge.amount)} />
        <Metric label="Edge count" value={text(edge.edge_count)} />
        <Metric label="Year range" value={`${text(edge.min_year)}-${text(edge.max_year)}`} />
        <Metric label="Evidence" value={edge.is_inferred ? "participant link" : text(edge.evidence_source)} />
      </div>
      <Info label="Years" value={Array.isArray(edge.years) ? edge.years.join(", ") : ""} />
      <Info label="Explanation" value={edge.is_inferred ? "This connector is derived from loop participant linkage so the circular path remains visible when transfer edge evidence is incomplete." : "This transfer edge is loaded from available loop edge records."} />
      <Actions loopId={graph.loop_id} />
    </div>
  );
}

function TransferList({ title, edges, direction }: { title: string; edges: GraphEdge[]; direction: "in" | "out" }) {
  return (
    <section>
      <h4 className="mb-2 text-sm font-semibold">{title}</h4>
      <div className="space-y-2">
        {edges.length === 0 && <div className="rounded-lg bg-[var(--surface-muted)] p-3 text-xs text-[var(--muted)]">No edges in this direction.</div>}
        {edges.slice(0, 8).map((edge) => (
          <div key={edge.id} className="rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] p-3 text-xs">
            <div className="font-semibold">{direction === "out" ? edge.target_name : edge.source_name}</div>
            <div className="mt-1 text-[var(--muted)]">{money(edge.amount)} · {text(edge.min_year)}-{text(edge.max_year)}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Info({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-3">
      <div className="text-xs uppercase text-[var(--muted)]">{label}</div>
      <div className="mt-1 text-sm">{text(value)}</div>
    </div>
  );
}

function Actions({ loopId, org }: { loopId: string; org?: string }) {
  const chatHref = org ? `/chat?loop=${encodeURIComponent(loopId)}` : `/chat?loop=${encodeURIComponent(loopId)}`;
  return (
    <div className="grid gap-2">
      <a href={chatHref} className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2 text-sm font-semibold hover:bg-[var(--surface)]">
        <Bot size={15} />
        Ask LoopLens
      </a>
      <a href={`/memo?loop=${encodeURIComponent(loopId)}`} className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2 text-sm font-semibold hover:bg-[var(--surface)]">
        <FileText size={15} />
        Generate memo
      </a>
      <a href={`/loops/detail?loop=${encodeURIComponent(loopId)}`} className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2 text-sm font-semibold hover:bg-[var(--surface)]">
        <ExternalLink size={15} />
        View loop details
      </a>
    </div>
  );
}
