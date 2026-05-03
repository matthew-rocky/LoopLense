from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


try:
    import plotly.express as px
except Exception:  # pragma: no cover
    px = None


COLORS = ["#2563eb", "#0f766e", "#7c3aed", "#d97706", "#475569", "#16a34a"]


def polish(fig: Any, title: str = "") -> Any:
    fig.update_layout(
        title={"text": title, "x": 0.01, "xanchor": "left", "font": {"size": 18, "color": "#0f172a"}},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, Segoe UI, Arial, sans-serif", "color": "#334155"},
        margin={"l": 20, "r": 20, "t": 58 if title else 24, "b": 24},
        height=410,
        legend_title_text="",
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#e2e8f0")
    fig.update_yaxes(gridcolor="#e2e8f0", zeroline=False)
    return fig


def render(df: pd.DataFrame, chart: dict[str, Any], key_prefix: str = "chart") -> None:
    ctype = str(chart.get("type") or "table")
    title = str(chart.get("title") or "")
    x = chart.get("x")
    y = chart.get("y")
    color = chart.get("color")
    if df.empty:
        st.info("No rows were returned for this question.")
        return
    if ctype == "metric":
        cols = st.columns(min(len(df.columns), 4) or 1)
        row = df.iloc[0].to_dict()
        for i, (name, value) in enumerate(row.items()):
            cols[i % len(cols)].metric(str(name), f"{value:,.0f}" if isinstance(value, (int, float)) else str(value))
        return
    if ctype == "bar" and x in df.columns and y in df.columns:
        if px:
            fig = px.bar(
                df,
                x=x,
                y=y,
                color=color if color in df.columns else None,
                title=title,
                color_discrete_sequence=COLORS,
            )
            st.plotly_chart(polish(fig, title), use_container_width=True, key=f"{key_prefix}_bar")
        else:
            st.bar_chart(df.set_index(x)[y])
        return
    if ctype == "line" and x in df.columns and y in df.columns:
        if px:
            fig = px.line(df, x=x, y=y, color=color if color in df.columns else None, title=title, color_discrete_sequence=COLORS)
            st.plotly_chart(polish(fig, title), use_container_width=True, key=f"{key_prefix}_line")
        else:
            st.line_chart(df.set_index(x)[y])
        return
    if ctype == "scatter" and x in df.columns and y in df.columns and px:
        fig = px.scatter(df, x=x, y=y, color=color if color in df.columns else None, title=title, color_discrete_sequence=COLORS)
        st.plotly_chart(polish(fig, title), use_container_width=True, key=f"{key_prefix}_scatter")
        return
    if ctype in {"hist", "histogram", "distribution"} and x in df.columns and px:
        fig = px.histogram(df, x=x, title=title, color_discrete_sequence=["#2563eb"])
        st.plotly_chart(polish(fig, title), use_container_width=True, key=f"{key_prefix}_histogram")
        return
    st.dataframe(df, use_container_width=True, height=360)
