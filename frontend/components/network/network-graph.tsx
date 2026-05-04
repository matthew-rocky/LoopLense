"use client";

import { memo, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  Background,
  EdgeLabelRenderer,
  Handle,
  MarkerType,
  Panel,
  Position,
  ReactFlow,
  getBezierPath,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Edge,
  type Node
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Maximize2, RefreshCw, RotateCcw, Scan, X, ZoomIn, ZoomOut } from "lucide-react";
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
  highlighted: boolean;
  muted: boolean;
  visible: boolean;
  active: boolean;
  size: number;
  delay: number;
  enterKey: string;
  connectionCount: number;
  evidenceCount: number;
  role: "source" | "return" | "participant";
  badges: string[];
} & Record<string, unknown>;

type EdgeData = {
  edge: GraphEdge;
  edgeKey: string;
  width: number;
  selected: boolean;
  highlighted: boolean;
  muted: boolean;
  hovered: boolean;
  visible: boolean;
  active: boolean;
  closing: boolean;
  delay: number;
  enterKey: string;
  yearLabel: string;
  labelOffset: number;
} & Record<string, unknown>;

type FlowNode = Node<NodeData, "org">;
type FlowEdge = Edge<EdgeData, "flow">;

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

function edgeKey(edge: GraphEdge, index: number) {
  return edge.id ?? `${edge.source}-${edge.target}-${edge.min_year ?? "start"}-${edge.max_year ?? "end"}-${index}`;
}

function edgeSignature(edge: GraphEdge) {
  return edge.id ?? [edge.source, edge.target, edge.amount ?? "", edge.min_year ?? "", edge.max_year ?? "", edge.evidence_source ?? ""].join("|");
}

function edgeYears(edge: GraphEdge) {
  if (Array.isArray(edge.years) && edge.years.length === 1) return String(edge.years[0]);
  if (Array.isArray(edge.years) && edge.years.length > 1) return `${edge.years[0]}-${edge.years[edge.years.length - 1]}`;
  if (edge.min_year || edge.max_year) return `${text(edge.min_year)}-${text(edge.max_year)}`;
  return "n/a";
}

function unique<T>(values: T[]) {
  return Array.from(new Set(values));
}

function pairKey(source: string, target: string) {
  return `${source}->${target}`;
}

const OrgNode = memo(function OrgNode({ data }: { data: NodeData }) {
  const node = data.node;
  const loc = location(node);
  return (
    <div
      key={`${node.id}-${data.enterKey}`}
      title={[
        node.label,
        `BN: ${node.bn ?? node.id}`,
        loc ? `Location: ${loc}` : "",
        `Sent: ${money(node.total_sent)}`,
        `Received: ${money(node.total_received)}`,
        `Outgoing edges: ${text(node.outgoing_edges)}`,
        `Incoming edges: ${text(node.incoming_edges)}`
      ]
        .filter(Boolean)
        .join("\n")}
      className={[
        "network-org-node relative rounded-[1.15rem] border px-4 py-3 text-left backdrop-blur transition duration-300",
        data.selected ? "is-selected" : "",
        data.highlighted ? "is-highlighted" : "",
        data.muted ? "is-muted" : "",
        data.visible ? "is-visible" : "is-hidden",
        data.active ? "is-trace-active" : "",
        data.role === "source" ? "is-source" : "",
        data.role === "return" ? "is-return" : "",
        node.is_cycle_node ? "is-cycle" : ""
      ].join(" ")}
      style={{ width: data.size, animationDelay: `${data.delay}ms` }}
    >
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !border-0 !bg-[var(--accent)]" />
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !border-0 !bg-[var(--accent)]" />
      <div className="network-node-sheen" />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="line-clamp-2 text-sm font-bold leading-5 text-[var(--foreground)]">{node.label}</div>
          <div className="mt-1 text-[10px] font-medium text-[var(--muted)]">{node.bn ?? node.id}</div>
          {loc && <div className="mt-1 truncate text-[10px] text-[var(--muted)]">{loc}</div>}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          {data.badges.map((badge) => (
            <span key={badge} className="network-node-badge">
              {badge}
            </span>
          ))}
          {node.position_in_loop !== null && node.position_in_loop !== undefined && (
            <span className="rounded-full border border-[var(--border)] bg-[var(--surface-muted)] px-2 py-0.5 text-[10px] font-semibold">
              #{String(node.position_in_loop)}
            </span>
          )}
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-[10px]">
        <div className="network-node-metric">
          <div className="text-[var(--muted)]">Sent</div>
          <div className="truncate font-semibold">{money(node.total_sent)}</div>
        </div>
        <div className="network-node-metric">
          <div className="text-[var(--muted)]">Received</div>
          <div className="truncate font-semibold">{money(node.total_received)}</div>
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between gap-2 text-[10px] text-[var(--muted)]">
        <span>{text(data.connectionCount)} links</span>
        <span>{text(data.evidenceCount)} evidence</span>
      </div>
    </div>
  );
});

function CurvedFlowEdge(props: any) {
  const { id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, markerEnd, data } = props;
  const safeId = String(id).replace(/[^a-zA-Z0-9_-]/g, "");
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    curvature: data.closing ? 0.58 : 0.42
  });
  const edge = data.edge as GraphEdge;
  const selected = Boolean(data.selected);
  const highlighted = Boolean(data.highlighted);
  const hovered = Boolean(data.hovered);
  const muted = Boolean(data.muted);
  const visible = Boolean(data.visible);
  const active = Boolean(data.active);
  const width = Number(data.width) || 2;
  const showDetails = selected || hovered;
  const showAmount = visible && (showDetails || highlighted || edge.is_cycle_edge || width >= 4);
  const stroke = !visible
    ? "transparent"
    : selected
    ? "var(--accent-2)"
    : active || highlighted || hovered || edge.is_cycle_edge
      ? "var(--accent)"
      : `url(#network-edge-gradient-${safeId})`;
  const labelOffset = Number(data.labelOffset) || 0;

  return (
    <>
      <defs>
        <linearGradient id={`network-edge-gradient-${safeId}`} gradientUnits="userSpaceOnUse" x1={sourceX} y1={sourceY} x2={targetX} y2={targetY}>
          <stop offset="0%" stopColor="color-mix(in srgb, var(--accent) 72%, transparent)" />
          <stop offset="58%" stopColor="var(--accent)" />
          <stop offset="100%" stopColor="var(--accent-2)" />
        </linearGradient>
      </defs>
      <path
        key={`${id}-${data.enterKey}`}
        id={id}
        className={[
          "react-flow__edge-path network-flow-edge",
          selected ? "is-selected" : "",
          highlighted ? "is-highlighted" : "",
          hovered ? "is-hovered" : "",
          muted ? "is-muted" : "",
          visible ? "is-visible" : "is-hidden",
          active ? "is-active" : "",
          data.closing ? "is-closing" : ""
        ].join(" ")}
        d={edgePath}
        fill="none"
        markerEnd={markerEnd}
        pathLength={1}
        style={{
          stroke,
          strokeWidth: selected ? width + 1.6 : hovered ? width + 0.9 : width,
          animationDelay: `${data.delay}ms`
        }}
      />
      {active && (
        <path className="network-flow-edge-trace" d={edgePath} fill="none" pathLength={1} strokeWidth={Math.max(3, width + 2)} />
      )}
      <path className="network-flow-hit" d={edgePath} fill="none" stroke="transparent" strokeWidth={Math.max(18, width + 10)} style={{ pointerEvents: visible ? "stroke" : "none" }} />
      {showAmount && (
        <EdgeLabelRenderer>
          <div
            className={[
              "network-edge-label pointer-events-none absolute rounded-xl border px-2.5 py-1.5 text-[10px] font-semibold backdrop-blur",
              showDetails ? "is-expanded" : "",
              muted ? "is-muted" : "",
              data.closing ? "is-closing" : ""
            ].join(" ")}
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY + labelOffset}px)` }}
            title={`${edge.source_name} -> ${edge.target_name}\nAmount: ${money(edge.amount)}\nYear: ${data.yearLabel}\nEvidence: ${text(edge.evidence_source)}`}
          >
            {showDetails ? (
              <div className="min-w-[190px] space-y-1">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-[var(--muted)]">Transfer</span>
                  <span className="text-[var(--accent)]">{money(edge.amount)}</span>
                </div>
                <div className="truncate">{edge.source_name ?? edge.source}</div>
                <div className="truncate text-[var(--muted)]">to {edge.target_name ?? edge.target}</div>
                <div className="flex items-center justify-between gap-3 text-[var(--muted)]">
                  <span>{data.yearLabel}</span>
                  <span>{edge.is_inferred ? "participant link" : text(edge.evidence_source)}</span>
                </div>
              </div>
            ) : (
              <span>{money(edge.amount)}</span>
            )}
          </div>
        </EdgeLabelRenderer>
      )}
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
  onToggleFocus,
  loadKey,
  children
}: {
  graph: NetworkGraph;
  year?: number | "all";
  selected: Selection;
  onSelect: (selection: Selection) => void;
  focusMode: boolean;
  onToggleFocus: () => void;
  loadKey: number;
  children?: ReactNode;
}) {
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([] as FlowNode[]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([] as FlowEdge[]);
  const [traceRun, setTraceRun] = useState(0);
  const [traceStep, setTraceStep] = useState(0);
  const [tracing, setTracing] = useState(true);
  const layoutKey = `${graph.loop_id}-${loadKey}`;
  const layoutKeyRef = useRef("");
  const layoutNodesRef = useRef<FlowNode[]>([]);
  const panelOpen = Boolean(selected);
  const fitPadding = panelOpen ? 0.34 : 0.28;

  const filteredEdges = useMemo(() => {
    if (!year || year === "all") return graph.edges;
    return graph.edges.filter((edge) => Array.isArray(edge.years) && edge.years.includes(year));
  }, [graph.edges, year]);

  const visibleNodeIds = useMemo(() => new Set(filteredEdges.flatMap((edge) => [edge.source, edge.target])), [filteredEdges]);
  const maxNodeFlow = useMemo(() => Math.max(1, ...graph.nodes.map(importance)), [graph.nodes]);
  const maxEdgeAmount = useMemo(() => Math.max(1, ...filteredEdges.map((edge) => n(edge.amount))), [filteredEdges]);
  const selectedEdgeSignature = selected?.type === "edge" ? edgeSignature(selected.item) : null;

  const orderedNodeIds = useMemo(() => {
    const graphNodeIds = new Set(graph.nodes.map((node) => node.id));
    const pathIds = unique((graph.highlight_circular_path ?? []).map(String).filter((id) => graphNodeIds.has(id)));
    if (pathIds.length > 0) return pathIds;
    return graph.nodes
      .slice()
      .sort((a, b) => {
        const aPos = Number(a.position_in_loop);
        const bPos = Number(b.position_in_loop);
        if (Number.isFinite(aPos) && Number.isFinite(bPos)) return aPos - bPos;
        return a.label.localeCompare(b.label);
      })
      .map((node) => node.id);
  }, [graph.highlight_circular_path, graph.nodes]);

  const trace = useMemo(() => {
    const nodeSteps = new Map<string, number>();
    const edgeSteps = new Map<string, number>();
    const path = orderedNodeIds.length > 0 ? orderedNodeIds : graph.nodes.map((node) => node.id);
    path.forEach((id, index) => nodeSteps.set(id, index));
    if (path.length > 1) {
      path.forEach((id, index) => {
        const target = path[(index + 1) % path.length];
        edgeSteps.set(pairKey(id, target), index === path.length - 1 ? path.length : index + 1);
      });
    }
    return {
      nodeSteps,
      edgeSteps,
      sourceId: path[0],
      closingSourceId: path.length > 1 ? path[path.length - 1] : undefined,
      maxStep: Math.max(1, path.length)
    };
  }, [graph.nodes, orderedNodeIds]);

  const highlight = useMemo(() => {
    const nodeIds = new Set<string>();
    const edgeIds = new Set<string>();
    if (!selected) return { nodeIds, edgeIds };

    if (selected.type === "node") {
      nodeIds.add(selected.item.id);
      filteredEdges.forEach((edge, index) => {
        if (edge.source === selected.item.id || edge.target === selected.item.id) {
          edgeIds.add(edgeKey(edge, index));
          nodeIds.add(edge.source);
          nodeIds.add(edge.target);
        }
      });
      return { nodeIds, edgeIds };
    }

    filteredEdges.forEach((edge, index) => {
      if (edgeSignature(edge) === selectedEdgeSignature) {
        edgeIds.add(edgeKey(edge, index));
        nodeIds.add(edge.source);
        nodeIds.add(edge.target);
      }
    });
    return { nodeIds, edgeIds };
  }, [filteredEdges, selected, selectedEdgeSignature]);

  const connectionCounts = useMemo(() => {
    const counts = new Map<string, number>();
    graph.edges.forEach((edge) => {
      counts.set(edge.source, (counts.get(edge.source) ?? 0) + 1);
      counts.set(edge.target, (counts.get(edge.target) ?? 0) + 1);
    });
    return counts;
  }, [graph.edges]);

  const evidenceCounts = useMemo(() => {
    const counts = new Map<string, number>();
    graph.edges.forEach((edge) => {
      const count = Math.max(1, n(edge.edge_count));
      counts.set(edge.source, (counts.get(edge.source) ?? 0) + count);
      counts.set(edge.target, (counts.get(edge.target) ?? 0) + count);
    });
    return counts;
  }, [graph.edges]);

  useEffect(() => {
    setTraceStep(0);
    setTracing(true);
    setTraceRun((value) => value + 1);
  }, [layoutKey]);

  useEffect(() => {
    if (!tracing) return;
    if (traceStep > trace.maxStep) {
      setTracing(false);
      return;
    }
    const delay = traceStep === 0 ? 620 : 880;
    const id = window.setTimeout(() => setTraceStep((step) => step + 1), delay);
    return () => window.clearTimeout(id);
  }, [trace.maxStep, traceRun, traceStep, tracing]);

  const replayTrace = useCallback(() => {
    setTraceStep(0);
    setTracing(true);
    setTraceRun((value) => value + 1);
  }, []);

  const baseNodes = useMemo<FlowNode[]>(() => {
    const visibleNodes = graph.nodes
      .filter((node) => visibleNodeIds.size === 0 || visibleNodeIds.has(node.id) || node.is_cycle_node)
      .sort((a, b) => (trace.nodeSteps.get(a.id) ?? 9999) - (trace.nodeSteps.get(b.id) ?? 9999) || a.label.localeCompare(b.label));
    const count = Math.max(visibleNodes.length, 1);
    const radiusX = Math.max(330, Math.min(660, count * 74));
    const radiusY = Math.max(240, Math.min(460, count * 52));
    const centerX = radiusX + 290;
    const centerY = radiusY + 190;

    return visibleNodes.map((node, index) => {
      const angle = (index / count) * Math.PI * 2 - Math.PI / 2;
      const outerOffset = node.is_cycle_node ? 0 : 92;
      const flowRatio = Math.log10(importance(node) + 10) / Math.log10(maxNodeFlow + 10);
      const size = Math.round(218 + flowRatio * 76);
      const selectedNode = selected?.type === "node" && selected.item.id === node.id;
      const highlighted = Boolean(selected && highlight.nodeIds.has(node.id));
      const step = trace.nodeSteps.get(node.id) ?? trace.maxStep + 1;
      const visible = !tracing || step <= traceStep;
      const role = node.id === trace.sourceId ? "source" : node.id === trace.closingSourceId ? "return" : "participant";
      const badges = [
        selectedNode ? "selected" : "",
        role === "source" ? "source" : role === "return" ? "return node" : "participant",
        role === "source" && trace.closingSourceId ? "loop closes" : ""
      ].filter(Boolean);
      return {
        id: node.id,
        type: "org",
        data: {
          node,
          selected: selectedNode,
          highlighted,
          muted: Boolean(selected && !highlight.nodeIds.has(node.id)),
          visible,
          active: tracing && step === traceStep,
          size,
          delay: 0,
          enterKey: `${layoutKey}-${traceRun}`,
          connectionCount: connectionCounts.get(node.id) ?? 0,
          evidenceCount: evidenceCounts.get(node.id) ?? 0,
          role,
          badges
        },
        position: {
          x: centerX + Math.cos(angle) * (radiusX + outerOffset) - size / 2,
          y: centerY + Math.sin(angle) * (radiusY + outerOffset) - 70
        }
      };
    });
  }, [connectionCounts, evidenceCounts, graph.nodes, highlight.nodeIds, layoutKey, maxNodeFlow, selected, trace, traceRun, traceStep, tracing, visibleNodeIds]);

  const baseEdges = useMemo<FlowEdge[]>(
    () =>
      filteredEdges.map((edge, index) => {
        const key = edgeKey(edge, index);
        const step = trace.edgeSteps.get(pairKey(edge.source, edge.target)) ?? trace.maxStep + 1;
        const visible = !tracing || step <= traceStep;
        const active = tracing && step === traceStep;
        const closing = Boolean(trace.closingSourceId && edge.source === trace.closingSourceId && edge.target === trace.sourceId);
        const amountRatio = Math.log10(n(edge.amount) + 10) / Math.log10(maxEdgeAmount + 10);
        const selectedEdge = selected?.type === "edge" && edgeSignature(edge) === selectedEdgeSignature;
        const highlighted = Boolean(selected && highlight.edgeIds.has(key));
        const color = !visible
          ? "transparent"
          : selectedEdge
          ? "var(--accent-2)"
          : highlighted || edge.is_cycle_edge
            ? "var(--accent)"
            : "color-mix(in srgb, var(--muted) 70%, transparent)";
        return {
          id: key,
          source: edge.source,
          target: edge.target,
          type: "flow",
          markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18, color },
          data: {
            edge,
            edgeKey: key,
            width: 2.2 + amountRatio * 5.4,
            selected: selectedEdge,
            highlighted,
            muted: Boolean(selected && !highlighted),
            hovered: hoveredEdgeId === key,
            visible,
            active,
            closing,
            delay: 0,
            enterKey: `${layoutKey}-${traceRun}`,
            yearLabel: edgeYears(edge),
            labelOffset: closing ? -26 : index % 2 === 0 ? -16 : 18
          },
          zIndex: active || selectedEdge || hoveredEdgeId === key ? 24 : highlighted || closing || edge.is_cycle_edge ? 12 : 1
        };
      }),
    [filteredEdges, highlight.edgeIds, hoveredEdgeId, layoutKey, maxEdgeAmount, selected, selectedEdgeSignature, trace, traceRun, traceStep, tracing]
  );

  useEffect(() => {
    layoutNodesRef.current = baseNodes;
    setNodes((current) => {
      const isNewLayout = layoutKeyRef.current !== layoutKey;
      layoutKeyRef.current = layoutKey;
      if (isNewLayout) return baseNodes;

      const currentById = new Map(current.map((node) => [node.id, node]));
      return baseNodes.map((node) => {
        const existing = currentById.get(node.id);
        return existing ? { ...node, position: existing.position, dragging: existing.dragging } : node;
      });
    });
  }, [baseNodes, layoutKey, setNodes]);

  useEffect(() => {
    setEdges(baseEdges);
  }, [baseEdges, setEdges]);

  useEffect(() => {
    setHoveredEdgeId(null);
  }, [layoutKey, year]);

  const resetLayout = useCallback(() => {
    setNodes(layoutNodesRef.current);
  }, [setNodes]);

  const onNodeClick = useCallback((_event: unknown, node: any) => onSelect({ type: "node", item: node.data.node }), [onSelect]);
  const onEdgeClick = useCallback((_event: unknown, edge: any) => onSelect({ type: "edge", item: edge.data.edge }), [onSelect]);
  const onEdgeMouseEnter = useCallback((_event: unknown, edge: any) => setHoveredEdgeId(edge.id), []);
  const onEdgeMouseLeave = useCallback((_event: unknown, edge: any) => {
    setHoveredEdgeId((current) => (current === edge.id ? null : current));
  }, []);

  return (
    <div
      className={`network-graph-shell relative flex h-full min-h-[420px] flex-1 overflow-hidden rounded-2xl border border-[var(--border)] ${
        panelOpen ? "has-panel" : ""
      } ${
        focusMode ? "fixed inset-3 z-50" : ""
      }`}
    >
      <ReactFlow
        className="network-react-flow"
        style={{ minHeight: "420px" }}
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: fitPadding }}
        minZoom={0.16}
        maxZoom={1.9}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onEdgeMouseEnter={onEdgeMouseEnter}
        onEdgeMouseLeave={onEdgeMouseLeave}
        onPaneClick={() => onSelect(null)}
        nodesDraggable
        onlyRenderVisibleElements
        proOptions={{ hideAttribution: true }}
      >
        <Background color="var(--network-grid)" gap={30} />
        <GraphAutoFit layoutKey={layoutKey} panelOpen={panelOpen} fitPadding={fitPadding} />
        <GraphToolbar
          selected={Boolean(selected)}
          tracing={tracing}
          fitPadding={fitPadding}
          onToggleFocus={onToggleFocus}
          onResetLayout={resetLayout}
          onClearSelection={() => onSelect(null)}
          onReplayTrace={replayTrace}
        />
      </ReactFlow>
      {children}
    </div>
  );
}

function GraphAutoFit({ layoutKey, panelOpen, fitPadding }: { layoutKey: string; panelOpen: boolean; fitPadding: number }) {
  const { fitView, getViewport, setViewport } = useReactFlow();
  useEffect(() => {
    const timers: number[] = [];
    const duration = 760;
    const lift = panelOpen ? 42 : 58;
    timers.push(
      window.setTimeout(() => {
        void fitView({ padding: fitPadding, duration });
        timers.push(
          window.setTimeout(() => {
            const viewport = getViewport();
            setViewport({ ...viewport, y: viewport.y - lift }, { duration: 340 });
          }, duration + 40)
        );
      }, 90)
    );
    return () => timers.forEach((id) => window.clearTimeout(id));
  }, [fitPadding, fitView, getViewport, layoutKey, panelOpen, setViewport]);
  return null;
}

function GraphToolbar({
  selected,
  tracing,
  fitPadding,
  onToggleFocus,
  onResetLayout,
  onClearSelection,
  onReplayTrace
}: {
  selected: boolean;
  tracing: boolean;
  fitPadding: number;
  onToggleFocus: () => void;
  onResetLayout: () => void;
  onClearSelection: () => void;
  onReplayTrace: () => void;
}) {
  const { fitView, getViewport, setViewport, zoomIn, zoomOut } = useReactFlow();
  const fitGraph = useCallback(
    (duration = 650) => {
      void fitView({ padding: fitPadding, duration });
      window.setTimeout(() => {
        const viewport = getViewport();
        setViewport({ ...viewport, y: viewport.y - 58 }, { duration: 300 });
      }, duration + 40);
    },
    [fitPadding, fitView, getViewport, setViewport]
  );
  const reset = useCallback(() => {
    onResetLayout();
    window.requestAnimationFrame(() => fitGraph());
  }, [fitGraph, onResetLayout]);

  return (
    <Panel position="top-right" className="network-graph-controls flex gap-1.5 rounded-2xl border border-[var(--border)] p-1.5 backdrop-blur">
      <button title="Zoom in" onClick={() => zoomIn({ duration: 220 })}>
        <ZoomIn size={15} />
      </button>
      <button title="Zoom out" onClick={() => zoomOut({ duration: 220 })}>
        <ZoomOut size={15} />
      </button>
      <button title="Fit view" onClick={() => fitGraph()}>
        <Scan size={15} />
      </button>
      <button title="Reset layout" onClick={reset}>
        <RotateCcw size={15} />
      </button>
      <button title={tracing ? "Tracing flow" : "Replay flow trace"} onClick={onReplayTrace}>
        <RefreshCw size={15} className={tracing ? "animate-spin" : ""} />
      </button>
      <button title="Clear selection" onClick={onClearSelection} disabled={!selected}>
        <X size={15} />
      </button>
      <button title="Focus mode" onClick={onToggleFocus}>
        <Maximize2 size={15} />
      </button>
    </Panel>
  );
}
