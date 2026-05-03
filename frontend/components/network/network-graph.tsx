"use client";

import { memo, useCallback, useMemo } from "react";
import {
  Background,
  BaseEdge,
  Controls,
  EdgeLabelRenderer,
  Handle,
  MarkerType,
  Panel,
  Position,
  ReactFlow,
  useReactFlow,
  getBezierPath
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Maximize2, RotateCcw, Scan } from "lucide-react";
import type { NetworkGraph } from "@/lib/types";
import { money, text } from "@/lib/format";

type GraphNode = NetworkGraph["nodes"][number];
type GraphEdge = NetworkGraph["edges"][number];
type Selection =
  | { type: "node"; item: GraphNode }
  | { type: "edge"; item: GraphEdge }
  | null;

type NodeData = {
  node: GraphNode;
  selected: boolean;
  size: number;
};

type EdgeData = {
  edge: GraphEdge;
  width: number;
  selected: boolean;
};

function n(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function location(node: GraphNode) {
  return [node.city, node.province].filter(Boolean).join(", ");
}

function importance(node: GraphNode) {
  return n(node.total_sent) + n(node.total_received);
}

const OrgNode = memo(function OrgNode({ data }: { data: NodeData }) {
  const node = data.node;
  const loc = location(node);
  return (
    <div
      title={[
        node.label,
        `BN: ${node.bn ?? node.id}`,
        loc ? `Location: ${loc}` : "",
        `Sent: ${money(node.total_sent)}`,
        `Received: ${money(node.total_received)}`,
        `Outgoing edges: ${text(node.outgoing_edges)}`,
        `Incoming edges: ${text(node.incoming_edges)}`
      ].filter(Boolean).join("\n")}
      className={`relative rounded-[1.35rem] border bg-[var(--surface-strong)] px-4 py-3 text-left shadow-glow backdrop-blur transition duration-300 ${
        data.selected ? "scale-105 border-[var(--accent)] ring-4 ring-[var(--accent)]/20" : node.is_cycle_node ? "border-[var(--accent)]/55" : "border-[var(--border)]"
      }`}
      style={{ width: data.size }}
    >
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !border-0 !bg-[var(--accent)]" />
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !border-0 !bg-[var(--accent)]" />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="line-clamp-2 text-sm font-bold leading-5 text-[var(--foreground)]">{node.label}</div>
          <div className="mt-1 text-[10px] text-[var(--muted)]">{node.bn ?? node.id}</div>
          {loc && <div className="mt-1 text-[10px] text-[var(--muted)]">{loc}</div>}
        </div>
        {node.position_in_loop !== null && node.position_in_loop !== undefined && (
          <span className="shrink-0 rounded-full border border-[var(--border)] bg-[var(--surface-muted)] px-2 py-0.5 text-[10px] font-semibold">
            #{String(node.position_in_loop)}
          </span>
        )}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-[10px]">
        <div className="rounded-lg bg-[var(--surface-muted)] px-2 py-1">
          <div className="text-[var(--muted)]">Sent</div>
          <div className="font-semibold">{money(node.total_sent)}</div>
        </div>
        <div className="rounded-lg bg-[var(--surface-muted)] px-2 py-1">
          <div className="text-[var(--muted)]">Received</div>
          <div className="font-semibold">{money(node.total_received)}</div>
        </div>
      </div>
      {node.is_cycle_node && <div className="absolute -inset-1 -z-10 rounded-[1.6rem] bg-[var(--accent)]/12 blur-md" />}
    </div>
  );
});

function CurvedFlowEdge(props: any) {
  const { id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, markerEnd, data } = props;
  const [edgePath, labelX, labelY] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition, curvature: 0.34 });
  const edge = data.edge as GraphEdge;
  const selected = Boolean(data.selected);
  const width = Number(data.width) || 2;
  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          strokeWidth: width,
          stroke: selected || edge.is_cycle_edge ? "var(--accent)" : "color-mix(in srgb, var(--muted) 58%, transparent)",
          filter: selected || edge.is_cycle_edge ? "drop-shadow(0 0 8px color-mix(in srgb, var(--accent) 62%, transparent))" : undefined,
          strokeDasharray: edge.is_inferred ? "8 6" : undefined,
          animation: edge.is_cycle_edge ? "dash 1.8s linear infinite" : undefined
        }}
      />
      <EdgeLabelRenderer>
        <div
          className="pointer-events-none absolute rounded-full border border-[var(--border)] bg-[var(--surface-strong)] px-2 py-1 text-[10px] font-semibold shadow-sm backdrop-blur"
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          title={`${edge.source_name} -> ${edge.target_name}\nAmount: ${money(edge.amount)}\nEdges: ${text(edge.edge_count)}\nYears: ${text(edge.years)}`}
        >
          {money(edge.amount)}
          {edge.is_inferred && <span className="ml-1 text-[var(--muted)]">link</span>}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

const nodeTypes = { org: OrgNode };
const edgeTypes = { flow: CurvedFlowEdge };

export function NetworkGraphView({
  graph,
  year,
  selected,
  onSelect,
  focusMode,
  onToggleFocus
}: {
  graph: NetworkGraph;
  year?: number | "all";
  selected: Selection;
  onSelect: (selection: Selection) => void;
  focusMode: boolean;
  onToggleFocus: () => void;
}) {
  const filteredEdges = useMemo(() => {
    if (!year || year === "all") return graph.edges;
    return graph.edges.filter((edge) => Array.isArray(edge.years) && edge.years.includes(year));
  }, [graph.edges, year]);

  const visibleNodeIds = useMemo(() => new Set(filteredEdges.flatMap((edge) => [edge.source, edge.target])), [filteredEdges]);
  const maxNodeFlow = useMemo(() => Math.max(1, ...graph.nodes.map(importance)), [graph.nodes]);
  const maxEdgeAmount = useMemo(() => Math.max(1, ...filteredEdges.map((edge) => n(edge.amount))), [filteredEdges]);

  const nodes = useMemo(
    () =>
      graph.nodes
        .filter((node) => visibleNodeIds.size === 0 || visibleNodeIds.has(node.id) || node.is_cycle_node)
        .map((node, index, list) => {
          const angle = (index / Math.max(list.length, 1)) * Math.PI * 2 - Math.PI / 2;
          const radius = Math.max(250, Math.min(560, list.length * 68));
          const offset = node.is_cycle_node ? 0 : 70;
          const flowRatio = Math.log10(importance(node) + 10) / Math.log10(maxNodeFlow + 10);
          return {
            id: node.id,
            type: "org",
            data: {
              node,
              selected: selected?.type === "node" && selected.item.id === node.id,
              size: Math.round(210 + flowRatio * 80)
            } satisfies NodeData,
            position: {
              x: Math.cos(angle) * (radius + offset) + radius + 150,
              y: Math.sin(angle) * (radius + offset) + radius + 110
            }
          };
        }),
    [graph.nodes, maxNodeFlow, selected, visibleNodeIds]
  );

  const edges = useMemo(
    () =>
      filteredEdges.map((edge, index) => {
        const amountRatio = Math.log10(n(edge.amount) + 10) / Math.log10(maxEdgeAmount + 10);
        return {
          id: edge.id ?? `${edge.source}-${edge.target}-${index}`,
          source: edge.source,
          target: edge.target,
          type: "flow",
          animated: true,
          markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18, color: edge.is_cycle_edge ? "var(--accent)" : "color-mix(in srgb, var(--muted) 70%, transparent)" },
          data: {
            edge,
            width: 2 + amountRatio * 5,
            selected: selected?.type === "edge" && selected.item.id === edge.id
          } satisfies EdgeData
        };
      }),
    [filteredEdges, maxEdgeAmount, selected]
  );

  const onNodeClick = useCallback((_event: unknown, node: any) => onSelect({ type: "node", item: node.data.node }), [onSelect]);
  const onEdgeClick = useCallback((_event: unknown, edge: any) => onSelect({ type: "edge", item: edge.data.edge }), [onSelect]);

  return (
    <div className={`relative h-full min-h-[650px] overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface-muted)] ${focusMode ? "fixed inset-3 z-50" : ""}`}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        minZoom={0.15}
        maxZoom={1.8}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onPaneClick={() => onSelect(null)}
      >
        <Background color="rgba(148,163,184,.30)" gap={28} />
        <Controls />
        <GraphToolbar onToggleFocus={onToggleFocus} />
      </ReactFlow>
    </div>
  );
}

function GraphToolbar({ onToggleFocus }: { onToggleFocus: () => void }) {
  const { fitView, setViewport } = useReactFlow();
  return (
    <Panel position="top-right" className="flex gap-2">
      <button className="rounded-lg border border-[var(--border)] bg-[var(--surface-strong)] p-2 shadow-sm transition hover:bg-[var(--surface)]" title="Fit graph to view" onClick={() => fitView({ padding: 0.18, duration: 700 })}>
        <Scan size={16} />
      </button>
      <button className="rounded-lg border border-[var(--border)] bg-[var(--surface-strong)] p-2 shadow-sm transition hover:bg-[var(--surface)]" title="Reset zoom" onClick={() => setViewport({ x: 0, y: 0, zoom: 0.7 }, { duration: 650 })}>
        <RotateCcw size={16} />
      </button>
      <button className="rounded-lg border border-[var(--border)] bg-[var(--surface-strong)] p-2 shadow-sm transition hover:bg-[var(--surface)]" title="Focus mode" onClick={onToggleFocus}>
        <Maximize2 size={16} />
      </button>
    </Panel>
  );
}
