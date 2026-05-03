from __future__ import annotations

from typing import Any

import networkx as nx
import plotly.graph_objects as go

from src.graph import edge_table


def _get(row: dict[str, Any], *names: str, default: Any = "") -> Any:
    for name in names:
        if row.get(name) not in (None, ""):
            return row[name]
    return default


def _label(bn: str, people: list[dict[str, Any]]) -> str:
    for person in people:
        pbn = str(_get(person, "bn", "BN", "charity_bn", "business_number"))
        if pbn == str(bn):
            name = _get(person, "name", "charity_name", "legal_name", default="")
            return f"{name}<br>{bn}" if name else str(bn)
    return str(bn)


def graph_edges(edges: list[dict[str, Any]], people: list[dict[str, Any]]) -> go.Figure:
    rows = [r for r in edge_table(edges) if r["from"] and r["to"]]
    fig = go.Figure()
    if not rows:
        fig.update_layout(title="No edge records available for the selected loop")
        return fig

    graph = nx.DiGraph()
    for row in rows:
        graph.add_edge(str(row["from"]), str(row["to"]), amount=row["amount"], year=row["year"])
    pos = nx.spring_layout(graph, seed=7, k=1.15, iterations=80)

    ex: list[float] = []
    ey: list[float] = []
    for src, dst, _data in graph.edges(data=True):
        x0, y0 = pos[src]
        x1, y1 = pos[dst]
        ex += [x0, x1, None]
        ey += [y0, y1, None]

    fig.add_trace(
        go.Scatter(
            x=ex,
            y=ey,
            mode="lines",
            line=dict(width=2.4, color="#94a3b8"),
            hoverinfo="none",
        )
    )

    for src, dst, data in graph.edges(data=True):
        x0, y0 = pos[src]
        x1, y1 = pos[dst]
        amount = data.get("amount", "")
        try:
            amount = f"${float(amount):,.0f}"
        except (TypeError, ValueError):
            amount = str(amount)
        fig.add_annotation(
            x=(x0 + x1) / 2,
            y=(y0 + y1) / 2,
            text=amount,
            showarrow=False,
            font=dict(size=10, color="#334155"),
            bgcolor="rgba(248,250,252,.92)",
            bordercolor="#cbd5e1",
            borderpad=3,
        )

    nxv = [pos[n][0] for n in graph.nodes]
    nyv = [pos[n][1] for n in graph.nodes]
    labels = [_label(str(n), people) for n in graph.nodes]
    fig.add_trace(
        go.Scatter(
            x=nxv,
            y=nyv,
            mode="markers+text",
            text=[str(n) for n in graph.nodes],
            hovertext=labels,
            hoverinfo="text",
            textposition="bottom center",
            marker=dict(size=30, color="#2563eb", line=dict(width=3, color="white")),
        )
    )
    fig.update_layout(
        height=620,
        margin=dict(l=8, r=8, t=20, b=8),
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font=dict(family="Inter, Segoe UI, Arial, sans-serif", color="#334155"),
    )
    return fig
