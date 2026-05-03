from __future__ import annotations

import uuid
from typing import Any, Callable

import pandas as pd

from src.data import TableInfo, find_col, preferred
from src.graph import edge_table
from src.llm import bedrock_ready
from src.query import run
from src.text import clean
from src.verify import build_memo, verify_chat_answer, verify_memo


PROMPTS = [
    "Show me the review label distribution.",
    "Show the top 10 loops by review score.",
    "Which loop has the largest circular flow?",
    "Show government funding exposure by review label.",
    "Which charities appear most often in loops?",
    "Show the distribution of circular flow values.",
    "Why was this loop flagged?",
    "Show the participants in the selected loop.",
    "Show the network for this loop.",
    "Generate a neutral memo for this loop.",
]

SAFE_ERROR = (
    "I could not answer that question from the current loaded data. Try asking about review labels, top loops, "
    "circular flow, frequent charities, the selected loop, or memo generation."
)


def qcol(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def qcols(cols: list[str]) -> str:
    return ", ".join(qcol(c) for c in cols)


def records(df: pd.DataFrame | None) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    return df.astype(object).where(pd.notnull(df), None).to_dict("records")


def frame(value: Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value
    if isinstance(value, list):
        return pd.DataFrame(value)
    if isinstance(value, dict):
        return pd.DataFrame([value])
    return pd.DataFrame()


def make_response(
    content: str,
    intent: str,
    data: pd.DataFrame | list[dict[str, Any]] | None = None,
    chart: dict[str, Any] | None = None,
    method: str = "",
    evidence: pd.DataFrame | list[dict[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    df = frame(data)
    ev = frame(evidence)
    return {
        "role": "assistant",
        "_id": uuid.uuid4().hex,
        "content": clean(content),
        "intent": intent,
        "data": records(df),
        "rows_used": records(df),
        "evidence": records(ev) if not ev.empty else records(df.head(20)),
        "chart": chart or {"type": "table", "title": "Result"},
        "sql": method,
        "error": None,
        **extra,
    }


def add_verification(response: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    intent = str(response.get("intent") or "unsupported")
    rows_used = response.get("rows_used") or response.get("data") or []
    response["verification"] = verify_chat_answer(
        answer_text=str(response.get("content") or ""),
        rows_used=rows_used,
        data_context=ctx,
        intent=intent,
    )
    if intent == "memo":
        response["memo_verification"] = verify_memo(
            response.get("memo") or response.get("content") or "",
            ctx.get("selected_loop") if isinstance(ctx.get("selected_loop"), dict) else {},
            ctx.get("selected_people") or [],
            ctx.get("selected_edges") or [],
            response.get("evidence") or [],
        )
    return response


def friendly_missing(message: str) -> dict[str, Any]:
    return make_response(message, "unsupported", pd.DataFrame([{"message": message}]), {"type": "table", "title": "Unavailable"})


def loop_meta(tables: dict[str, TableInfo]) -> tuple[str | None, dict[str, str | None]]:
    table = preferred(tables, "loops")
    if not table:
        return None, {}
    cols = tables[table].columns
    return table, {
        "loop_id": find_col(cols, ["loop_id", "id", "cycle_id", "component_id"]),
        "label": find_col(cols, ["review_label"], ["label"]),
        "score": find_col(cols, ["review_score"], ["score"]),
        "flow": find_col(cols, ["total_flow", "score_total_flow", "total_flow_allyears", "total_flow_window"], ["flow"]),
        "govt": find_col(cols, ["loop_max_govt_share_pct", "score_govt_share_pct", "max_govt_share_pct", "total_govt_all_years"], ["govt"]),
        "why": find_col(cols, ["why_flagged"], ["why", "reason"]),
    }


def people_meta(tables: dict[str, TableInfo]) -> tuple[str | None, dict[str, str | None]]:
    table = preferred(tables, "people")
    if not table:
        return None, {}
    cols = tables[table].columns
    return table, {
        "loop_id": find_col(cols, ["loop_id", "id", "cycle_id", "component_id"]),
        "bn": find_col(cols, ["bn", "charity_bn", "business_number"]),
        "name": find_col(cols, ["legal_name", "charity_name", "account_name", "name"]),
    }


def query(ctx: dict[str, Any], sql: str) -> pd.DataFrame:
    df, err = run(ctx["con"], sql)
    if err:
        raise RuntimeError(err)
    return df


def answer_label_distribution(ctx: dict[str, Any]) -> dict[str, Any]:
    table, m = loop_meta(ctx["tables"])
    if not table or not m.get("label"):
        return friendly_missing("I could not find a review label column in the loaded loop data.")
    sql = f"SELECT {qcol(m['label'])} AS review_label, COUNT(*) AS loops FROM {table} GROUP BY 1 ORDER BY loops DESC"
    df = query(ctx, sql)
    return make_response(
        "This shows how many loaded loops fall into each review-priority label.",
        "label_distribution",
        df,
        {"type": "bar", "x": "review_label", "y": "loops", "title": "Review Label Distribution"},
        sql,
    )


def answer_top_loops(ctx: dict[str, Any]) -> dict[str, Any]:
    table, m = loop_meta(ctx["tables"])
    if not table or not m.get("score"):
        return friendly_missing("I could not find a review score column in the loaded data, so I cannot rank loops by score.")
    cols = [c for c in [m.get("loop_id"), m.get("label"), m.get("score"), m.get("flow"), m.get("why")] if c]
    sql = f"SELECT {qcols(cols)} FROM {table} ORDER BY {qcol(m['score'])} DESC LIMIT 10"
    df = query(ctx, sql)
    return make_response(
        "These are the top loaded loops by deterministic review score.",
        "top_loops",
        df,
        {"type": "bar", "x": m.get("loop_id") or cols[0], "y": m["score"], "title": "Top 10 Loops by Review Score"},
        sql,
    )


def answer_largest_flow(ctx: dict[str, Any]) -> dict[str, Any]:
    table, m = loop_meta(ctx["tables"])
    if not table or not m.get("flow"):
        return friendly_missing("I could not find a circular flow column in the loaded data.")
    cols = [c for c in [m.get("loop_id"), m.get("label"), m.get("score"), m.get("flow"), m.get("why")] if c]
    sql = f"SELECT {qcols(cols)} FROM {table} ORDER BY {qcol(m['flow'])} DESC LIMIT 1"
    df = query(ctx, sql)
    return make_response(
        "This is the loop with the largest available circular flow value.",
        "largest_flow",
        df,
        {"type": "table", "title": "Largest Circular Flow"},
        sql,
    )


def answer_government_exposure(ctx: dict[str, Any]) -> dict[str, Any]:
    table, m = loop_meta(ctx["tables"])
    if not table or not m.get("label") or not m.get("govt"):
        return friendly_missing("I could not find both review label and government exposure indicator columns.")
    sql = (
        f"SELECT {qcol(m['label'])} AS review_label, AVG({qcol(m['govt'])}) AS avg_govt_exposure_indicator, "
        f"COUNT(*) AS loops FROM {table} WHERE {qcol(m['govt'])} IS NOT NULL GROUP BY 1 ORDER BY avg_govt_exposure_indicator DESC"
    )
    df = query(ctx, sql)
    return make_response(
        "This compares the available government funding exposure indicator by review-priority label.",
        "government_exposure_by_label",
        df,
        {"type": "bar", "x": "review_label", "y": "avg_govt_exposure_indicator", "title": "Government Exposure Indicator by Label"},
        sql,
    )


def answer_charity_frequency(ctx: dict[str, Any]) -> dict[str, Any]:
    table, m = people_meta(ctx["tables"])
    if not table or not m.get("bn"):
        return friendly_missing("I could not find participant charity identifiers in the loaded data.")
    label_expr = f"COALESCE({qcol(m['name'])}, {qcol(m['bn'])})" if m.get("name") else qcol(m["bn"])
    sql = f"SELECT {label_expr} AS charity, COUNT(*) AS loop_appearances FROM {table} GROUP BY 1 ORDER BY loop_appearances DESC LIMIT 10"
    df = query(ctx, sql)
    return make_response(
        "These charities or entities appear most often in the loaded loop participant records.",
        "charity_frequency",
        df,
        {"type": "bar", "x": "charity", "y": "loop_appearances", "title": "Most Frequent Loop Participants"},
        sql,
    )


def answer_flow_distribution(ctx: dict[str, Any]) -> dict[str, Any]:
    table, m = loop_meta(ctx["tables"])
    if not table or not m.get("flow"):
        return friendly_missing("I could not find a circular flow column in the loaded data.")
    sql = f"SELECT {qcol(m['flow'])} AS circular_flow FROM {table} WHERE {qcol(m['flow'])} IS NOT NULL"
    df = query(ctx, sql)
    stats = pd.to_numeric(df["circular_flow"], errors="coerce").dropna()
    evidence = pd.DataFrame(
        [
            {"stat": "count", "value": int(stats.count()) if not stats.empty else 0},
            {"stat": "median", "value": float(stats.median()) if not stats.empty else None},
            {"stat": "mean", "value": float(stats.mean()) if not stats.empty else None},
            {"stat": "max", "value": float(stats.max()) if not stats.empty else None},
        ]
    )
    return make_response(
        "This histogram shows how available circular flow values are distributed.",
        "flow_distribution",
        df,
        {"type": "histogram", "x": "circular_flow", "title": "Circular Flow Distribution"},
        sql,
        evidence=evidence,
    )


def selected_loop_missing(ctx: dict[str, Any]) -> bool:
    return not ctx.get("selected_loop_id") or not ctx.get("selected_loop")


def answer_selected_loop_explanation(ctx: dict[str, Any]) -> dict[str, Any]:
    if selected_loop_missing(ctx):
        return friendly_missing("Please select a loop first, or choose an example loop.")
    row = ctx["selected_loop"]
    table, m = loop_meta(ctx["tables"])
    cols = [c for c in [m.get("loop_id"), m.get("label"), m.get("score"), m.get("flow"), m.get("govt"), m.get("why")] if c]
    evidence = pd.DataFrame([{c: row.get(c) for c in cols}])
    method = f"Selected loop row from {table}; fields: {', '.join(cols)}"
    return make_response(
        "The selected loop was flagged by deterministic review-priority indicators available in the loaded records.",
        "selected_loop_explanation",
        evidence,
        {"type": "table", "title": "Selected Loop Evidence"},
        method,
        evidence=evidence,
    )


def answer_selected_loop_participants(ctx: dict[str, Any]) -> dict[str, Any]:
    if selected_loop_missing(ctx):
        return friendly_missing("Please select a loop first, or choose an example loop.")
    df = pd.DataFrame(ctx.get("selected_people") or [])
    return make_response(
        "These are participant records for the selected loop.",
        "selected_loop_participants",
        df,
        {"type": "table", "title": "Selected Loop Participants"},
        "Participant rows filtered by the selected loop id.",
        evidence=df,
    )


def answer_selected_loop_network(ctx: dict[str, Any]) -> dict[str, Any]:
    if selected_loop_missing(ctx):
        return friendly_missing("Please select a loop first, or choose an example loop.")
    edges = ctx.get("selected_edges") or []
    people = ctx.get("selected_people") or []
    df = pd.DataFrame(edge_table(edges))
    response = make_response(
        "This network shows available transfer edges for the selected loop.",
        "selected_loop_network",
        df,
        {"type": "network", "title": "Selected Loop Network"},
        "Edge rows filtered by the selected loop id.",
        evidence=pd.DataFrame(people),
    )
    response["edge_records"] = edges
    response["people_records"] = people
    return response


def answer_memo(ctx: dict[str, Any]) -> dict[str, Any]:
    if selected_loop_missing(ctx):
        return friendly_missing("Please select a loop first, or choose an example loop.")
    result = build_memo(
        ctx.get("selected_loop") or {},
        ctx.get("selected_edges") or [],
        ctx.get("selected_people") or [],
        use_llm=bedrock_ready(),
    )
    memo = result["memo"]
    checks = pd.DataFrame(result["checks"])
    return make_response(
        memo.get("summary", "Generated an evidence-grounded memo for the selected loop."),
        "memo",
        pd.DataFrame([ctx.get("selected_loop") or {}]),
        {"type": "none", "title": "Memo"},
        "Memo generated from selected loop, edge, and participant rows.",
        evidence=checks,
        memo=memo,
        memo_checks=records(checks),
    )


def route_intent(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ["memo", "review memo", "summarize this loop"]):
        return "memo"
    if any(w in q for w in ["network", "visualize", "graph"]):
        return "selected_loop_network"
    if any(w in q for w in ["participant", "who is involved", "list the charities", "entities in this loop"]):
        return "selected_loop_participants"
    if any(w in q for w in ["why", "flagged", "high priority", "explain", "indicator", "evidence supports"]):
        return "selected_loop_explanation"
    if any(w in q for w in ["government", "exposure", "funding share"]):
        return "government_exposure_by_label"
    if any(w in q for w in ["histogram", "flow distribution", "distribution of circular flow", "flow values", "flow amounts distributed"]):
        return "flow_distribution"
    if any(w in q for w in ["largest", "biggest", "largest circular flow", "largest transfer loop"]):
        return "largest_flow"
    if any(w in q for w in ["charities appear", "appear most", "most frequent", "entities appear", "frequency"]):
        return "charity_frequency"
    if any(w in q for w in ["top", "highest priority", "rank", "review score", "by score"]):
        return "top_loops"
    if any(w in q for w in ["how many loops", "label distribution", "review label distribution", "high, medium", "high medium", "labels"]):
        return "label_distribution"
    return "unsupported"


HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "label_distribution": answer_label_distribution,
    "top_loops": answer_top_loops,
    "largest_flow": answer_largest_flow,
    "government_exposure_by_label": answer_government_exposure,
    "charity_frequency": answer_charity_frequency,
    "flow_distribution": answer_flow_distribution,
    "selected_loop_explanation": answer_selected_loop_explanation,
    "selected_loop_participants": answer_selected_loop_participants,
    "selected_loop_network": answer_selected_loop_network,
    "memo": answer_memo,
}


def handle_prompt(question: str, data_context: dict[str, Any], selected_loop_id: str | None = None, demo_mode: bool = False) -> dict[str, Any]:
    ctx = dict(data_context)
    ctx["selected_loop_id"] = selected_loop_id or data_context.get("selected_loop_id")
    try:
        intent = route_intent(question)
        handler = HANDLERS.get(intent)
        if not handler:
            return add_verification(
                friendly_missing(
                    "I can answer questions about the loaded LoopLens dataset, such as review labels, scores, circular flows, participants, selected-loop evidence, and neutral memos."
                ),
                ctx,
            )
        return add_verification(handler(ctx), ctx)
    except Exception as exc:
        response = friendly_missing(SAFE_ERROR)
        response["error"] = str(exc)
        return add_verification(response, ctx)
