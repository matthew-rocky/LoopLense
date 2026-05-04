"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, Network, Pause, Play, Search, Square } from "lucide-react";
import { getNetwork } from "@/lib/api";
import type { AnyRow, NetworkGraph } from "@/lib/types";
import { loopId, money, score, text } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { InvestigationPanel } from "./investigation-panel";
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

export function NetworkWorkspace({ initialLoopId, initialGraph, loopOptions }: { initialLoopId: string; initialGraph?: NetworkGraph; loopOptions: AnyRow[] }) {
  const [loop, setLoop] = useState(initialLoopId);
  const [graph, setGraph] = useState<NetworkGraph | undefined>(initialGraph);
  const [selected, setSelected] = useState<Selection>(null);
  const [year, setYear] = useState<number | "all">("all");
  const [playing, setPlaying] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [graphLoadKey, setGraphLoadKey] = useState(0);
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
      setGraphLoadKey((value) => value + 1);
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

  const stopTimeline = useCallback(() => {
    setPlaying(false);
    setYear("all");
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
    }, 1300);
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
  }, []);

  const clearSelection = useCallback(() => {
    setSelected(null);
  }, []);

  return (
    <div className="network-workspace flex min-h-[560px] flex-1 flex-col overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)]">
      <div className="grid shrink-0 gap-3 border-b border-[var(--border)] bg-[var(--surface-strong)] p-3 xl:grid-cols-[1fr_auto_auto] xl:p-4">
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
          {loopOptions.map((row) => (
            <option key={loopId(row)} value={loopId(row)}>
              {Array.isArray(row.participant_names) ? row.participant_names.slice(0, 2).join(", ") : loopId(row)}
            </option>
          ))}
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

      <div className="relative flex min-h-0 flex-1 p-3 xl:p-4">
        {loading && (
          <div className="absolute inset-4 z-50 grid place-items-center rounded-2xl bg-[var(--surface)]/70 backdrop-blur">
            <div className="flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface-strong)] px-4 py-3 text-sm shadow-glow">
              <Loader2 className="animate-spin text-[var(--accent)]" size={18} />
              Building intelligence map...
            </div>
          </div>
        )}
        {graph && graph.nodes.length > 0 ? (
          <NetworkGraphView
            graph={graph}
            year={year}
            selected={selected}
            onSelect={handleSelect}
            focusMode={focusMode}
            onToggleFocus={() => setFocusMode((value) => !value)}
            loadKey={graphLoadKey}
          >
            <InvestigationPanel selection={selected} graph={graph} onClose={clearSelection} />
            <YearControl year={year} setYear={setManualYear} years={availableYears} playing={playing} onTogglePlay={togglePlaying} onStop={stopTimeline} />
          </NetworkGraphView>
        ) : (
          <EmptyState icon={Network} title="No network selected" description="Select a loop to inspect the circular transfer path with organization names and BN metadata." />
        )}
      </div>
    </div>
  );
}

function YearControl({
  year,
  setYear,
  years,
  playing,
  onTogglePlay,
  onStop
}: {
  year: number | "all";
  setYear: (year: number | "all") => void;
  years: number[];
  playing: boolean;
  onTogglePlay: () => void;
  onStop: () => void;
}) {
  if (years.length === 0) {
    return (
      <div className="network-year-control pointer-events-auto absolute bottom-3 left-1/2 z-30 -translate-x-1/2 rounded-full border px-4 py-2 text-sm text-[var(--muted)] backdrop-blur">
        No year data
      </div>
    );
  }
  const selectedIndex = year === "all" ? 0 : Math.max(1, years.indexOf(year) + 1);
  const playDisabled = years.length <= 1;
  return (
    <div className="network-year-control pointer-events-auto absolute bottom-3 left-1/2 z-30 flex max-w-[calc(100%-2rem)] -translate-x-1/2 flex-wrap items-center justify-center gap-2 rounded-2xl border px-2 py-1.5 backdrop-blur md:flex-nowrap md:px-3">
      <button
        className="network-year-button"
        onClick={onTogglePlay}
        disabled={playDisabled}
        title={playing ? "Pause yearly transfer animation" : "Play yearly transfer animation"}
      >
        {playing ? <Pause size={16} /> : <Play size={16} />}
      </button>
      <button className="network-year-button" onClick={onStop} disabled={year === "all" && !playing} title="Stop timeline and show all years">
        <Square size={13} />
      </button>
      <select
        className="min-w-28 rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-2.5 py-1.5 text-sm font-semibold outline-none focus:focus-ring"
        value={year}
        onChange={(event) => setYear(event.target.value === "all" ? "all" : Number(event.target.value))}
        title="Select all years or a specific year"
      >
        <option value="all">All years</option>
        {years.map((item) => <option key={item} value={item}>{item}</option>)}
      </select>
      <div className="flex min-w-[220px] flex-1 items-center gap-2 md:min-w-[320px]">
        <span className="text-xs font-semibold text-[var(--muted)]">{years[0]}</span>
        <input
          className="network-year-range min-w-36 flex-1"
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
      <div className="min-w-20 rounded-full border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-1 text-center text-sm font-semibold">
        {year === "all" ? "All years" : year}
      </div>
    </div>
  );
}

function SummaryCards({ graph }: { graph: NetworkGraph }) {
  const summary = graph.summary ?? {};
  return (
    <div className="network-summary-grid grid shrink-0 gap-2 border-b border-[var(--border)] bg-[var(--surface-muted)] p-3 md:grid-cols-3 xl:grid-cols-7">
      <Metric label="Loop" value={graph.loop_id} />
      <Metric label="Participants" value={text(summary.participant_count ?? graph.nodes.length)} />
      <Metric label="Circular Flow" value={money(summary.circular_flow)} />
      <Metric label="Highest Edge" value={money(summary.highest_transfer_edge)} />
      <Metric label="Score" value={score(summary.score)} />
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3">
        <div className="text-xs text-[var(--muted)]">Priority</div>
        <div className="mt-2"><Badge label={summary.label} /></div>
      </div>
      <Metric label="Years / Edges" value={`${text(summary.min_year)}-${text(summary.max_year)} / ${text(summary.total_edges)}`} />
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-2.5">
      <div className="text-xs text-[var(--muted)]">{label}</div>
      <div className="mt-1 truncate font-semibold">{value}</div>
    </div>
  );
}
