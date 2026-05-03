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
        "chart": chart if chart is not None else ({"type": "table", "title": "Result"} if not df.empty else None),
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
    return make_response(message, "unsupported", pd.DataFrame(), None, "", evidence=pd.DataFrame())


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
        "bottleneck": find_col(cols, ["bottleneck_amt", "score_bottleneck", "bottleneck_allyears", "bottleneck_window"], ["bottleneck"]),
        "participants": find_col(cols, ["participant_count"], ["participants"]),
        "govt": find_col(cols, ["loop_max_govt_share_pct", "score_govt_share_pct", "max_govt_share_pct", "total_govt_all_years"], ["govt"]),
        "overhead": find_col(cols, ["loop_max_strict_overhead_pct", "loop_max_broad_overhead_pct", "score_overhead_pct"], ["overhead"]),
        "path": find_col(cols, ["path_display", "path_bns"], ["path"]),
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


def display_value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, "", "nan", "NaN"):
            return value
    return None


def money(value: Any) -> str | None:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return f"${n:,.0f}"


def number(value: Any, digits: int = 1) -> str | None:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return f"{n:,.{digits}f}"


def ratio(value: Any) -> str | None:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if 0 <= n <= 1:
        return f"{n * 100:,.1f}%"
    if 1 < n <= 100:
        return f"{n:,.1f}%"
    return f"{n:,.2f} ratio indicator"


def selected_loop_columns(m: dict[str, str | None]) -> list[str]:
    return [
        c
        for c in [
            m.get("loop_id"),
            m.get("score"),
            m.get("label"),
            m.get("flow"),
            m.get("bottleneck"),
            m.get("participants"),
            m.get("govt"),
            m.get("overhead"),
            m.get("path"),
            m.get("why"),
        ]
        if c
    ]


def row_loop_id(row: dict[str, Any]) -> str | None:
    value = display_value(row, "loop_id", "id", "cycle_id", "component_id")
    return None if value is None else str(value)


def entity_name(row: dict[str, Any]) -> str:
    return str(display_value(row, "organization_name", "name", "legal_name", "charity_name", "account_name", "charity", "bn", "business_number", "entity_id") or "Unknown organization")


def entity_role(row: dict[str, Any]) -> str:
    sends_to = display_value(row, "sends_to", "target_name", "to_name")
    receives_from = display_value(row, "receives_from", "source_name", "from_name")
    position = display_value(row, "position_in_loop", "participant_role", "role")
    if sends_to and receives_from:
        return f"Sends to {sends_to} and receives from {receives_from}"
    if sends_to:
        return f"Sends to {sends_to}"
    if receives_from:
        return f"Receives from {receives_from}"
    if position is not None:
        return f"Participant position {position} in the circular path"
    return "Participant in the circular path"


def participant_rows_for_loop(row: dict[str, Any], ctx: dict[str, Any]) -> list[dict[str, Any]]:
    loop_id = row_loop_id(row)
    selected_id = ctx.get("selected_loop_id")
    if loop_id and selected_id and str(loop_id) == str(selected_id):
        people = ctx.get("selected_people") or []
        if isinstance(people, list):
            return [p for p in people if isinstance(p, dict)]
    participants = row.get("participants")
    if isinstance(participants, list):
        return [p for p in participants if isinstance(p, dict)]
    return []


def build_entity_summary(rows: list[dict[str, Any]], limit: int = 6) -> str:
    if not rows:
        return ""
    lines = [f"It involves {len(rows)} organizations or entities:"]
    for index, row in enumerate(rows[:limit], start=1):
        details = [f"{index}. {entity_name(row)}"]
        bn = display_value(row, "bn", "BN", "charity_bn", "business_number", "registration_number", "entity_id")
        if bn:
            details.append(f"   Business/registration number: {bn}")
        details.append(f"   Role: {entity_role(row)}")
        sent = money(display_value(row, "total_sent", "sent_amount", "amount_sent"))
        received = money(display_value(row, "total_received", "received_amount", "amount_received"))
        govt = ratio(display_value(row, "max_govt_share_pct", "govt_share_pct", "loop_max_govt_share_pct", "score_govt_share_pct"))
        overhead = ratio(display_value(row, "max_strict_overhead_pct", "strict_overhead_pct", "loop_max_strict_overhead_pct", "score_overhead_pct"))
        location = ", ".join(str(v) for v in [display_value(row, "city"), display_value(row, "province")] if v)
        category = display_value(row, "category", "designation", "status", "filing_status", "source_dataset")
        if sent:
            details.append(f"   Total sent: {sent}")
        if received:
            details.append(f"   Total received: {received}")
        if govt:
            details.append(f"   Government funding share: {govt}")
        if overhead:
            details.append(f"   Overhead indicator: {overhead}")
        if location:
            details.append(f"   Location: {location}")
        if category:
            details.append(f"   Available classification/status: {category}")
        lines.extend(details)
    if len(rows) > limit:
        lines.append(f"...and {len(rows) - limit} more organizations or entities in the returned records.")
    return "\n".join(lines)


def summarize_loop(row: dict[str, Any], prefix: str, participants: list[dict[str, Any]] | None = None) -> str:
    loop_id = display_value(row, "loop_id", "id", "cycle_id", "component_id")
    score = number(display_value(row, "review_score", "score"))
    label = display_value(row, "review_label", "label")
    flow = money(display_value(row, "total_flow", "circular_flow", "score_total_flow", "total_flow_allyears", "total_flow_window"))
    participant_count = display_value(row, "participant_count")
    participant_rows = participants or []
    why = display_value(row, "why_flagged")
    path = display_value(row, "path_display")
    parts = [prefix]
    if loop_id is not None:
        parts.append(f"loop {loop_id}")
    if score is not None:
        parts.append(f"with a review score of {score}")
    if label is not None:
        parts.append(f"and a {label} review label")
    sentence = " ".join(parts).strip() + "."
    details: list[str] = []
    if flow is not None and participant_count is not None:
        details.append(f"It has a total circular flow of {flow} across {participant_count} organizations or entities.")
    elif flow is not None:
        details.append(f"It has a total circular flow of {flow}.")
    elif participant_count is not None:
        details.append(f"It includes {participant_count} organizations or entities.")
    if path:
        details.append(f"The circular path recorded for this loop is {path}.")
    entity_section = build_entity_summary(participant_rows)
    if entity_section:
        details.append(entity_section)
    if why:
        details.append(f"This loop is worth human review because of {why}.")
    details.append("This does not prove wrongdoing; it only means the loop is worth human review.")
    return " ".join([sentence, *details])


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
    cols = selected_loop_columns(m)
    sql = f"SELECT {qcols(cols)} FROM {table} ORDER BY {qcol(m['score'])} DESC LIMIT 10"
    df = query(ctx, sql)
    row = records(df.head(1))[0] if not df.empty else {}
    people = participant_rows_for_loop(row, ctx) if row else []
    answer = summarize_loop(row, "The highest-priority loaded loop is", people) if row else "These are the top loaded loops ranked by deterministic review score."
    return make_response(
        answer + (" The table includes the next highest-scoring loops for comparison." if len(df) > 1 else ""),
        "top_loops",
        df,
        {"type": "bar", "x": m.get("loop_id") or cols[0], "y": m["score"], "title": "Top 10 Loops by Review Score"},
        sql,
        evidence=pd.DataFrame(people) if people else None,
        suggested_followups=loop_followups(),
    )


def loop_followups() -> list[str]:
    return [
        "Show organization details",
        "Why was this loop flagged?",
        "Show evidence rows",
        "Generate neutral memo",
        "Show network view",
    ]


def participant_followups() -> list[str]:
    return [
        "Show organization details",
        "Why was this loop flagged?",
        "Show evidence rows",
        "Generate neutral memo",
        "Show network view",
    ]


def answer_worst_loop(ctx: dict[str, Any]) -> dict[str, Any]:
    table, m = loop_meta(ctx["tables"])
    if not table or not m.get("score"):
        return friendly_missing("I could not find a review score column in the loaded data, so I cannot identify the highest-priority loop.")
    cols = selected_loop_columns(m)
    sql = f"SELECT {qcols(cols)} FROM {table} ORDER BY {qcol(m['score'])} DESC LIMIT 1"
    df = query(ctx, sql)
    row = records(df.head(1))[0] if not df.empty else {}
    people = participant_rows_for_loop(row, ctx) if row else []
    return make_response(
        summarize_loop(row, "The highest-priority loop in the loaded dataset is", people) if row else "I could not find a loop row in the loaded dataset.",
        "worst_loop",
        df,
        {"type": "table", "title": "Highest-Priority Loop"},
        sql,
        evidence=pd.DataFrame(people) if people else None,
        suggested_followups=participant_followups(),
    )


def answer_largest_flow(ctx: dict[str, Any]) -> dict[str, Any]:
    table, m = loop_meta(ctx["tables"])
    if not table or not m.get("flow"):
        return friendly_missing("I could not find a circular flow column in the loaded data.")
    cols = selected_loop_columns(m)
    sql = f"SELECT {qcols(cols)} FROM {table} ORDER BY {qcol(m['flow'])} DESC LIMIT 1"
    df = query(ctx, sql)
    row = records(df.head(1))[0] if not df.empty else {}
    people = participant_rows_for_loop(row, ctx) if row else []
    return make_response(
        summarize_loop(row, "The loaded loop with the largest circular flow is", people) if row else "I could not find a loop with circular flow in the loaded data.",
        "largest_flow",
        df,
        {"type": "table", "title": "Largest Circular Flow"},
        sql,
        evidence=pd.DataFrame(people) if people else None,
        suggested_followups=loop_followups(),
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
    cols = selected_loop_columns(m)
    evidence = pd.DataFrame([{c: row.get(c) for c in cols}])
    people = ctx.get("selected_people") or []
    method = f"Selected loop row from {table}; fields: {', '.join(cols)}"
    return make_response(
        summarize_loop(row, "The current loop context is", [p for p in people if isinstance(p, dict)]),
        "selected_loop_explanation",
        evidence,
        {"type": "table", "title": "Selected Loop Evidence"},
        method,
        evidence=pd.DataFrame(people) if people else evidence,
        suggested_followups=loop_followups(),
    )


def answer_selected_loop_participants(ctx: dict[str, Any]) -> dict[str, Any]:
    if selected_loop_missing(ctx):
        return friendly_missing("Please select a loop first, or choose an example loop.")
    df = pd.DataFrame(ctx.get("selected_people") or [])
    people = records(df)
    loop = ctx.get("selected_loop") if isinstance(ctx.get("selected_loop"), dict) else {}
    loop_label = row_loop_id(loop) or str(ctx.get("selected_loop_id") or "selected")
    return make_response(
        f"Loop {loop_label} includes the following organizations or entities.\n\n{build_entity_summary(people) if people else 'No participant organization details were available in the loaded records.'}",
        "selected_loop_participants",
        df,
        {"type": "table", "title": "Selected Loop Participants"},
        "Participant rows filtered by the selected loop id.",
        evidence=df,
        suggested_followups=loop_followups(),
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
    if any(
        phrase in q
        for phrase in [
            "worst loop",
            "loop is worst",
            "riskiest loop",
            "most concerning loop",
            "highest risk loop",
            "highest priority loop",
            "most severe loop",
            "top risk loop",
        ]
    ):
        return "worst_loop"
    if any(w in q for w in ["memo", "review memo", "summarize this loop", "generate neutral memo", "neutral memo"]):
        return "memo"
    if any(w in q for w in ["network", "visualize", "graph", "network view"]):
        return "selected_loop_network"
    if any(
        w in q
        for w in [
            "participant",
            "who is involved",
            "which companies are involved",
            "companies involved",
            "organizations involved",
            "entities involved",
            "organization details",
            "company details",
            "show company details",
            "show organization details",
            "list the charities",
            "entities in this loop",
        ]
    ):
        return "selected_loop_participants"
    if any(w in q for w in ["why", "flagged", "suspicious", "tell me about this loop", "about this loop", "high priority", "explain", "indicator", "evidence supports", "evidence rows"]):
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
    "worst_loop": answer_worst_loop,
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
