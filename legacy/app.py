from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _in_streamlit_runtime() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


def _project_python() -> Path | None:
    name = "python.exe" if os.name == "nt" else "python"
    folder = "Scripts" if os.name == "nt" else "bin"
    candidate = ROOT / ".venv" / folder / name
    return candidate if candidate.exists() else None


def _ensure_project_python() -> None:
    if __name__ != "__main__" or _in_streamlit_runtime():
        return
    project_python = _project_python()
    if not project_python:
        return
    if Path(sys.executable).resolve() == project_python.resolve():
        return
    print(f"Restarting LoopLens with project interpreter: {project_python}", flush=True)
    os.execv(str(project_python), [str(project_python), str(Path(__file__).resolve())])


def _launch_streamlit_from_python_run() -> None:
    """Let VS Code's plain Python Run button start the Streamlit app."""
    if __name__ != "__main__":
        return
    if _in_streamlit_runtime():
        return

    print("Starting LoopLens with Streamlit...", flush=True)
    print("Open the local URL shown below if your browser does not open automatically.", flush=True)
    raise SystemExit(subprocess.call([sys.executable, "-m", "streamlit", "run", __file__]))


_ensure_project_python()
_launch_streamlit_from_python_run()

import pandas as pd
import polars as pl
import streamlit as st

from legacy.chat import render_chat_tab, render_verification_panel
from src.data import discover, find_col
from legacy.graph import graph_edges
from src.graph import edge_table
from src.llm import bedrock_ready
from src.load import get_edges, get_people, load_edges, load_loops, load_people, load_profiles
from src.query import connect, schema_text
from src.text import friendly_column, money, number, ratio_indicator, score, short_id
from legacy.ui import apply_theme, card_end, card_start, hero, info_card, metric_card, section, selected_loop_card
from src.verify import build_memo, verify_memo

try:
    import plotly.express as px
except Exception:  # pragma: no cover
    px = None


st.set_page_config(page_title="LoopLens | Public-Funding Review Workspace", page_icon="LL", layout="wide")
apply_theme()


@st.cache_data(show_spinner=False)
def cached_frames() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    return load_loops(), load_edges(), load_people(), load_profiles()


@st.cache_data(show_spinner=False)
def cached_tables():
    return discover()


@st.cache_resource(show_spinner=False)
def cached_conn(tables):
    return connect(tables)


def as_pd(df: pl.DataFrame) -> pd.DataFrame:
    return df.to_pandas() if not df.is_empty() else pd.DataFrame()


def first_col(df: pl.DataFrame, names: list[str], contains: list[str] | None = None) -> str | None:
    return find_col(df.columns, names, contains)


def filter_loops(loops: pl.DataFrame, labels: list[str], score_range: tuple[int, int], min_flow: float, max_rows: int) -> pl.DataFrame:
    out = loops
    if not out.is_empty() and "review_label" in out.columns and labels:
        out = out.filter(pl.col("review_label").is_in(labels))
    if not out.is_empty() and "review_score" in out.columns:
        out = out.filter(pl.col("review_score").fill_null(0).is_between(score_range[0], score_range[1]))
    flow = first_col(out, ["total_flow", "score_total_flow", "bottleneck_amt"], ["flow"]) if not out.is_empty() else None
    if flow and min_flow > 0:
        out = out.filter(pl.col(flow).cast(pl.Float64, strict=False).fill_null(0) >= min_flow)
    return out.head(max_rows)


def loop_options(loops: pl.DataFrame) -> list[dict[str, Any]]:
    if loops.is_empty():
        return []
    return loops.head(500).to_dicts()


def label_loop(row: dict[str, Any]) -> str:
    bits = [short_id(row), str(row.get("review_label", "Unscored"))]
    if row.get("review_score") not in (None, ""):
        bits.append(f"score {row.get('review_score')}")
    if row.get("total_flow") not in (None, ""):
        bits.append(money(row.get("total_flow")))
    return " | ".join(bits)


def display_df(df: pd.DataFrame, height: int = 420) -> None:
    if df.empty:
        st.info("No rows are available for this view.")
        return
    renamed = {col: friendly_column(col) for col in df.columns}
    st.dataframe(df.rename(columns=renamed), use_container_width=True, height=height, hide_index=True)


def flow_col(df: pl.DataFrame) -> str | None:
    return first_col(df, ["total_flow", "score_total_flow", "total_flow_allyears", "total_flow_window", "bottleneck_amt"], ["flow"])


def metric_row(loops: pl.DataFrame, people: pl.DataFrame, selected: dict[str, Any]) -> None:
    high = loops.filter(pl.col("review_label") == "High").height if "review_label" in loops.columns else 0
    med = loops.filter(pl.col("review_label") == "Medium").height if "review_label" in loops.columns else 0
    low = loops.filter(pl.col("review_label") == "Low").height if "review_label" in loops.columns else 0
    flow = flow_col(loops)
    total_flow = loops.select(pl.col(flow).cast(pl.Float64, strict=False).sum()).item() if flow else None
    charity_col = first_col(people, ["bn", "charity_bn", "business_number"]) if not people.is_empty() else None
    unique_charities = people.select(pl.col(charity_col).n_unique()).item() if charity_col else None
    selected_score = selected.get("review_score") if selected else None
    cards = [
        ("Total loops", f"{loops.height:,}", "Loaded circular patterns"),
        ("High review priority", f"{high:,}", "Needs earlier human review"),
        ("Medium review priority", f"{med:,}", "Review queue candidates"),
        ("Low review priority", f"{low:,}", "Lower-priority indicators"),
        ("Total circular flow", money(total_flow) if total_flow is not None else "n/a", "Available flow field"),
        ("Unique charities/entities", f"{unique_charities:,}" if unique_charities is not None else "n/a", "Participant records"),
        ("Selected loop score", score(selected_score), "Active loop context"),
    ]
    cols = st.columns(len(cards))
    for col, (label, value, helper) in zip(cols, cards):
        with col:
            metric_card(label, value, helper)


tables = cached_tables()
con = cached_conn(tables)
loops, edges, people, profiles = cached_frames()

hero()

if loops.is_empty():
    st.warning("Processed loop data is missing. Run `python scripts/build_data.py`, then restart Streamlit.")
    with st.expander("Detected processed files"):
        st.json({name: {"path": str(info.path), "columns": info.columns} for name, info in tables.items()})
    st.stop()

labels_available = sorted(loops.get_column("review_label").drop_nulls().unique().to_list()) if "review_label" in loops.columns else []
st.sidebar.markdown("## LoopLens Controls")
st.sidebar.markdown('<div class="data-status">Data loaded from local processed files. Charts and chatbot answers use available records.</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sidebar-title">Demo</div>', unsafe_allow_html=True)
demo_mode = st.sidebar.toggle("Demo Mode", value=False)
st.sidebar.caption("Demo Mode chooses a strong example loop when possible.")
st.sidebar.markdown('<div class="sidebar-title">Filters</div>', unsafe_allow_html=True)
if st.sidebar.button("Reset filters", use_container_width=True):
    st.session_state["_reset_filters"] = True
reset = st.session_state.pop("_reset_filters", False)
labels = st.sidebar.multiselect("Review label", labels_available, default=labels_available if not reset else labels_available)
score_range = st.sidebar.slider("Review score range", 0, 100, (0, 100))
flow_filter = flow_col(loops)
min_flow = st.sidebar.number_input("Minimum circular flow", min_value=0.0, value=0.0, step=1000.0, disabled=flow_filter is None)
max_rows = st.sidebar.slider("Rows shown", 25, 1000, 250, step=25)

filtered = filter_loops(loops, labels, score_range, min_flow, max_rows)
options = loop_options(filtered if not filtered.is_empty() else loops)
default_index = 0
if demo_mode and options:
    for i, row in enumerate(options):
        if row.get("review_label") == "High":
            default_index = i
            break
st.sidebar.markdown('<div class="sidebar-title">Selected Loop</div>', unsafe_allow_html=True)
selected = st.sidebar.selectbox("Selected loop", options, index=default_index, format_func=label_loop) if options else {}
selected_id = short_id(selected)
selected_edges = get_edges(selected_id, edges)
selected_people = get_people(selected_id, people)
st.sidebar.caption(label_loop(selected) if selected else "No loop selected.")

metric_row(loops, people, selected)

tabs = st.tabs([
    "Executive Overview",
    "Loop Explorer",
    "Network View",
    "Ask LoopLens",
    "Memo and Verification",
    "Methodology",
])

with tabs[0]:
    section("Executive Overview", "Triage summary for loaded circular transfer patterns. Labels are review-priority indicators only.")
    selected_loop_card(
        selected_id,
        selected.get("review_label", "Unscored") if selected else "n/a",
        score(selected.get("review_score")) if selected else "n/a",
        money(selected.get(flow_col(loops))) if selected and flow_col(loops) else "n/a",
        len(selected_people) if selected_people else None,
    )
    left, right = st.columns(2)
    with left:
        card_start()
        if "review_label" in loops.columns:
            counts = as_pd(loops.group_by("review_label").len().sort("len", descending=True))
            if px:
                fig = px.bar(counts, x="review_label", y="len", title="Review Label Distribution", color="review_label",
                             color_discrete_sequence=["#2563eb", "#0f766e", "#d97706", "#64748b"])
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=390, margin=dict(l=10, r=10, t=55, b=20))
                fig.update_yaxes(gridcolor="#e2e8f0")
                fig.update_xaxes(showgrid=False)
                st.plotly_chart(fig, use_container_width=True, key="overview_label_distribution")
            else:
                st.bar_chart(counts.set_index("review_label")["len"])
        else:
            st.info("No review label column was found.")
        card_end()
    with right:
        card_start()
        if "review_score" in loops.columns:
            top = as_pd(loops.sort("review_score", descending=True).head(10))
            top["loop"] = top.apply(lambda r: str(r.get("loop_id") or r.get("id") or r.name), axis=1)
            if px:
                fig = px.bar(top, x="review_score", y="loop", orientation="h", title="Top Review-Priority Loops",
                             color_discrete_sequence=["#2563eb"])
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=390, margin=dict(l=10, r=10, t=55, b=20))
                fig.update_xaxes(gridcolor="#e2e8f0")
                fig.update_yaxes(showgrid=False, categoryorder="total ascending")
                st.plotly_chart(fig, use_container_width=True, key="overview_top_loops")
            else:
                st.bar_chart(top.set_index("loop")["review_score"])
        else:
            st.info("No review score column was found.")
        card_end()
    bottom_left, bottom_right = st.columns([1.2, 1])
    with bottom_left:
        card_start()
        fcol = flow_col(loops)
        if fcol and px:
            flow_df = as_pd(loops.select(pl.col(fcol).cast(pl.Float64, strict=False).alias("circular_flow")).drop_nulls())
            fig = px.histogram(flow_df, x="circular_flow", title="Circular Flow Distribution", color_discrete_sequence=["#0f766e"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=330, margin=dict(l=10, r=10, t=55, b=20))
            fig.update_yaxes(gridcolor="#e2e8f0")
            st.plotly_chart(fig, use_container_width=True, key="overview_flow_distribution")
        else:
            st.info("No circular flow field was available for a distribution chart.")
        card_end()
    with bottom_right:
        st.markdown(
            """
            <div class="insight-list">
              <strong>Reviewer focus</strong><br>
              Start with high review-priority loops, inspect the circular flow and bottleneck values, then use
              Network View and Ask LoopLens to validate participants, transfer edges, and evidence-grounded memo claims.
            </div>
            """,
            unsafe_allow_html=True,
        )
    section("Selected Loop Snapshot", "The active loop used by Network View, Ask LoopLens, and Memo and Verification.")
    display_df(pd.DataFrame([selected]), height=160)

with tabs[1]:
    section("Loop Explorer", "Filtered loop records. Use the sidebar to narrow labels, score range, and circular flow.")
    selected_loop_card(
        selected_id,
        selected.get("review_label", "Unscored") if selected else "n/a",
        score(selected.get("review_score")) if selected else "n/a",
        money(selected.get(flow_col(loops))) if selected and flow_col(loops) else "n/a",
        len(selected_people) if selected_people else None,
    )
    visible = as_pd(filtered)
    preferred_cols = [
        c for c in ["loop_id", "review_label", "review_score", "total_flow", "score_total_flow", "bottleneck_amt", "participant_count", "why_flagged"]
        if c in visible.columns
    ]
    rest = [c for c in visible.columns if c not in preferred_cols]
    display_df(visible[preferred_cols + rest] if preferred_cols else visible, height=520)
    section("Selected Loop Details", "Field-level view for the loop currently active in the sidebar.")
    detail = pd.DataFrame([selected]).T.reset_index()
    detail.columns = ["field", "value"]
    detail["value"] = detail["value"].map(lambda x: ", ".join(map(str, x)) if isinstance(x, list) else str(x))
    display_df(detail, height=360)

with tabs[2]:
    section(f"Network View: {selected_id}", "Edges represent available transfer records for the selected loop.")
    selected_loop_card(
        selected_id,
        selected.get("review_label", "Unscored") if selected else "n/a",
        score(selected.get("review_score")) if selected else "n/a",
        money(selected.get(flow_col(loops))) if selected and flow_col(loops) else "n/a",
        len(selected_people) if selected_people else None,
    )
    if selected_edges:
        card_start()
        st.caption("Nodes represent charities or entities. Directed edges represent available transfer records for the selected loop.")
        st.plotly_chart(graph_edges(selected_edges, selected_people), use_container_width=True, key=f"network_view_{selected_id}")
        card_end()
        section("Edge Table")
        display_df(pd.DataFrame(edge_table(selected_edges)), height=300)
        if selected_people:
            section("Participant Table")
            display_df(pd.DataFrame(selected_people), height=300)
    else:
        st.info("No edge records were available for the selected loop.")

with tabs[3]:
    data_context = {
        "tables": tables,
        "con": con,
        "selected_loop": selected,
        "selected_loop_id": selected_id if selected else None,
        "selected_edges": selected_edges,
        "selected_people": selected_people,
    }
    render_chat_tab(data_context, selected_loop_id=selected_id if selected else None, demo_mode=demo_mode)

with tabs[4]:
    section(f"Memo and Verification: {selected_id}", "Evidence-grounded memo with claim checks against selected loop data.")
    selected_loop_card(
        selected_id,
        selected.get("review_label", "Unscored") if selected else "n/a",
        score(selected.get("review_score")) if selected else "n/a",
        money(selected.get(flow_col(loops))) if selected and flow_col(loops) else "n/a",
        len(selected_people) if selected_people else None,
    )
    use_llm = st.toggle("Use AWS Bedrock if configured", value=bedrock_ready())
    result = build_memo(selected, selected_edges, selected_people, use_llm=use_llm)
    memo = result["memo"]
    if memo.get("warning"):
        st.warning(memo["warning"])
    st.markdown('<div class="memo-card">', unsafe_allow_html=True)
    st.markdown(f"### {memo.get('title', 'Review-priority memo')}")
    st.write(memo.get("summary", ""))
    st.markdown("#### Findings")
    for item in memo.get("findings", []):
        st.write(f"- {item}")
    st.markdown("#### Rationale")
    st.write(memo.get("rationale", ""))
    st.markdown("#### Next Steps")
    for item in memo.get("next_steps", []):
        st.write(f"- {item}")
    st.info(memo.get("disclaimer", "This memo is not a finding of wrongdoing."))
    st.markdown("</div>", unsafe_allow_html=True)
    section("Memo Verification", "Claim-level checks compare memo wording with selected loop, participant, and edge evidence.")
    memo_ver = verify_memo(memo, selected, selected_people, selected_edges, result.get("checks", []))
    render_verification_panel(memo_ver, claim_level=True)
    with st.expander("Structured memo claim checks", expanded=False):
        display_df(pd.DataFrame(result["checks"]), height=320)

with tabs[5]:
    section("Methodology", "How LoopLens computes and explains review-priority indicators.")
    c1, c2 = st.columns(2)
    with c1:
        info_card(
            "What LoopLens does",
            "LoopLens treats circular funding patterns as review-priority indicators. Labels help human reviewers triage records and inspect evidence.",
            "Review workspace",
        )
        info_card(
            "Scoring approach",
            "Scores are deterministic and use available fields such as circular flow, bottleneck amount, government exposure indicators, overhead context, repeated participation, and same-year indicators.",
            "Deterministic indicators",
        )
        info_card(
            "Ask LoopLens architecture",
            "Common questions are answered with deterministic local handlers over DuckDB-backed files. AWS Bedrock is optional for neutral wording and memo phrasing.",
            "Data first",
        )
    with c2:
        info_card(
            "What LoopLens does not do",
            "LoopLens does not make findings of wrongdoing, intent, legal status, or misconduct. It does not replace a human reviewer.",
            "Bounded use",
        )
        info_card(
            "LLM Hallucination Guard",
            "Charts, tables, metrics, and network views are generated from attached rows. Verification checks numeric claims, entities, labels, participant counts, flow amounts, evidence availability, and risky wording.",
            "Grounding checks",
        )
        info_card(
            "Human review and limitations",
            "Verification reduces unsupported LLM output, but it does not eliminate uncertainty. Reviewers should inspect source rows, query details, and context before acting.",
            "Human review required",
        )
    with st.expander("Schema inspector", expanded=True):
        st.code(schema_text(tables) or "No processed tables detected.")
        display_df(pd.DataFrame([
            {"table": name, "kind": info.kind, "path": str(info.path), "rows": info.rows, "columns": ", ".join(info.columns)}
            for name, info in tables.items()
        ]), height=360)
