from __future__ import annotations

import uuid
from typing import Any, Callable

import pandas as pd
from src.data import TableInfo, find_col, preferred
from src.graph import edge_table
from src.llm import bedrock_ready, load_memory, save_memory
from src.query import run
from src.text import clean, money
from src.verify import build_memo, verify_chat_answer, verify_memo

st = None
charts = None
graph_edges = None
info_card = None
metric_card = None


def _ensure_streamlit() -> Any:
    global st
    if st is None:
        import streamlit as streamlit_module

        st = streamlit_module
    return st


def _ensure_render_deps() -> None:
    global charts, graph_edges, info_card, metric_card
    _ensure_streamlit()
    if charts is None:
        from legacy import charts as charts_module

        charts = charts_module
    if graph_edges is None:
        from legacy.graph import graph_edges as graph_edges_func

        graph_edges = graph_edges_func
    if info_card is None or metric_card is None:
        from legacy.ui import info_card as info_card_func, metric_card as metric_card_func

        info_card = info_card_func
        metric_card = metric_card_func


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


def lit(value: Any) -> str:
    return "'" + str(value).replace("'", "''") + "'"


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


def element_key(response: dict[str, Any], name: str) -> str:
    if "_id" not in response:
        response["_id"] = uuid.uuid4().hex
    return f"{name}_{response['_id']}"


def add_verification(response: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Attach deterministic grounding checks to every chat response."""
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


def friendly_missing(what: str) -> dict[str, Any]:
    return make_response(what, "unsupported", pd.DataFrame([{"message": what}]), {"type": "table", "title": "Unavailable"})


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


def edge_meta(tables: dict[str, TableInfo]) -> tuple[str | None, dict[str, str | None]]:
    table = preferred(tables, "edges")
    if not table:
        return None, {}
    cols = tables[table].columns
    return table, {
        "loop_id": find_col(cols, ["loop_id", "id", "cycle_id", "component_id"]),
        "src": find_col(cols, ["src", "from_bn", "source_bn", "donor_bn", "source"]),
        "dst": find_col(cols, ["dst", "to_bn", "target_bn", "donee_bn", "target"]),
        "amount": find_col(cols, ["total_amt", "amount", "total_amount", "flow_amount", "transfer_amount"]),
        "year": find_col(cols, ["year", "min_year", "max_year", "fiscal_year", "period"]),
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
        return friendly_missing("Please select a loop first, or turn on Demo Mode to use an example loop.")
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
        return friendly_missing("Please select a loop first, or turn on Demo Mode to use an example loop.")
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
        return friendly_missing("Please select a loop first, or turn on Demo Mode to use an example loop.")
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
        return friendly_missing("Please select a loop first, or turn on Demo Mode to use an example loop.")
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
        legacy_memo_checks=records(checks),
    )


def route_intent(question: str) -> str:
    q = question.lower()
    # Order is intentionally specific-to-broad.
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
            return add_verification(friendly_missing(
                "I can answer questions about the loaded LoopLens dataset, such as review labels, scores, circular flows, participants, selected-loop evidence, and neutral memos."
            ), ctx)
        return add_verification(handler(ctx), ctx)
    except Exception as exc:
        response = friendly_missing(SAFE_ERROR)
        response["error"] = str(exc)
        return add_verification(response, ctx)


def metric_cards(df: pd.DataFrame) -> None:
    _ensure_render_deps()
    if df.empty:
        return
    cols = st.columns(min(len(df), 4) or 1)
    for i, row in df.head(4).iterrows():
        name = str(row.get("review_label", row.iloc[0]))
        val = row.get("loops", row.iloc[-1])
        with cols[i % len(cols)]:
            metric_card(name, f"{val:,.0f}" if isinstance(val, (int, float)) else str(val), "Loaded loops")


def render_memo(response: dict[str, Any]) -> None:
    _ensure_render_deps()
    memo = response.get("memo") or {}
    st.markdown('<div class="memo-card">', unsafe_allow_html=True)
    st.markdown(f"### {memo.get('title', 'Evidence-grounded memo')}")
    st.write(memo.get("summary", ""))
    if memo.get("findings"):
        st.markdown("**Key indicators**")
        for item in memo.get("findings", []):
            st.write(f"- {item}")
    if memo.get("rationale"):
        st.markdown("**Limitations**")
        st.write(memo["rationale"])
    if memo.get("next_steps"):
        st.markdown("**Suggested human-review questions**")
        for item in memo.get("next_steps", []):
            st.write(f"- {item}")
    if memo.get("disclaimer"):
        st.info(memo["disclaimer"])
    st.markdown("</div>", unsafe_allow_html=True)
    memo_ver = response.get("memo_verification")
    if memo_ver:
        st.markdown("#### Memo Verification")
        render_verification_panel(memo_ver, claim_level=True)
    checks = frame(response.get("legacy_memo_checks"))
    if not checks.empty:
        st.markdown("**Structured memo claim checks**")
        st.dataframe(checks, use_container_width=True)


def _status_class(status: str) -> str:
    low = status.lower()
    if "verified" in low and "mostly" not in low:
        return "verify-ok"
    if "mismatch" in low or "unsupported" in low:
        return "verify-bad"
    return "verify-warn"


def render_verification_panel(verification: dict[str, Any] | None, claim_level: bool = False) -> None:
    _ensure_render_deps()
    if not verification:
        st.info("No verification details were attached to this response.")
        return
    status = str(verification.get("overall_status") or verification.get("status") or "Needs review")
    st.markdown(
        f'<div class="verify-card"><span class="verify-badge {_status_class(status)}">{status}</span>'
        f'<div class="verify-summary">{verification.get("summary", "This response was checked against available rows.")}</div></div>',
        unsafe_allow_html=True,
    )
    meta = {
        "rows_used_count": verification.get("rows_used_count", 0),
        "source": verification.get("source", "deterministic verification"),
        "query_or_method_available": verification.get("query_or_method_available", True),
    }
    st.caption(
        "Verification reduces unsupported LLM output by checking generated text against rows used, "
        "but it does not remove the need for human review."
    )
    st.json(meta, expanded=False)
    checks = frame(verification.get("checks"))
    if not checks.empty:
        if claim_level:
            cols = [c for c in ["claim", "status", "evidence_field", "evidence_value", "explanation"] if c in checks.columns]
        else:
            cols = [c for c in ["check", "status", "claim", "evidence", "evidence_value", "explanation"] if c in checks.columns]
        st.dataframe(checks[cols] if cols else checks, use_container_width=True)
    failed = []
    for check in verification.get("checks") or []:
        if str(check.get("check", "")).lower() == "risky language check" and str(check.get("status", "")).lower() == "failed":
            failed.append(check)
        if str(check.get("status", "")).lower() in {"mismatch", "blocked"} and "accusatory" in str(check.get("explanation", "")).lower():
            failed.append(check)
    if failed:
        st.warning("Potentially accusatory language detected. LoopLens should use neutral review-priority wording.")


def render_chat_response(response: dict[str, Any]) -> None:
    _ensure_render_deps()
    st.markdown('<div class="chat-card">', unsafe_allow_html=True)
    st.write(response.get("content", ""))
    verification = response.get("verification") or {}
    status = str(verification.get("overall_status") or "Needs review")
    st.markdown(
        f'<span class="verify-badge {_status_class(status)}">{status}</span>',
        unsafe_allow_html=True,
    )
    intent = response.get("intent")
    df = frame(response.get("data"))
    evidence = frame(response.get("evidence"))
    chart = response.get("chart") or {"type": "table", "title": "Result"}

    if intent == "memo":
        render_memo(response)
    elif chart.get("type") == "network":
        edges = response.get("edge_records") or []
        people = response.get("people_records") or []
        if edges:
            st.plotly_chart(
                graph_edges(edges, people),
                use_container_width=True,
                key=element_key(response, "chat_network"),
            )
        else:
            st.info("No edge records were available for the selected loop.")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
    else:
        if intent == "label_distribution":
            metric_cards(df)
        if intent == "largest_flow" and not df.empty:
            row = df.iloc[0].to_dict()
            c1, c2, c3 = st.columns(3)
            with c1:
                metric_card("Loop", str(row.get("loop_id", row.get("id", "n/a"))), "Largest available flow")
            flow = next((row[k] for k in row if "flow" in str(k).lower()), None)
            with c2:
                metric_card("Circular flow", money(flow), "Available records")
            score = next((row[k] for k in row if "score" in str(k).lower()), "n/a")
            with c3:
                metric_card("Review score", str(score), "Deterministic indicator")
        charts.render(df, chart, key_prefix=element_key(response, "chat_chart"))
        if intent in {
            "label_distribution",
            "top_loops",
            "largest_flow",
            "government_exposure_by_label",
            "charity_frequency",
            "selected_loop_explanation",
            "selected_loop_participants",
        } and not df.empty:
            st.dataframe(df, use_container_width=True)
        if intent == "flow_distribution" and not evidence.empty:
            st.markdown("**Summary stats**")
            st.dataframe(evidence, use_container_width=True)

    with st.expander("Show query or method"):
        st.code(response.get("sql") or "No query was required.", language="sql")
    with st.expander("Show rows used"):
        rows = frame(response.get("rows_used"))
        st.dataframe(rows if not rows.empty else df, use_container_width=True)
    if not evidence.empty:
        with st.expander("Show evidence"):
            st.dataframe(evidence, use_container_width=True)
    with st.expander("Answer Verification"):
        render_verification_panel(response.get("verification"))
    if response.get("error"):
        with st.expander("Technical details"):
            st.code(response["error"])
    st.markdown("</div>", unsafe_allow_html=True)


def render_chat_tab(data_context: dict[str, Any], selected_loop_id: str | None = None, demo_mode: bool = False) -> None:
    _ensure_render_deps()
    info_card(
        "Ask LoopLens",
        "Ask natural-language questions about the loaded loop dataset. LoopLens converts questions into data-backed analytics, charts, tables, and neutral explanations.",
        "Evidence-grounded data assistant",
    )
    st.info("LoopLens is a review-priority tool, not an accusation system. It highlights patterns that may warrant human review.")
    st.caption("Demo-safe mode: deterministic local handlers answer common questions without Bedrock or LLM-generated SQL.")

    st.markdown("#### Suggested prompts")
    for start in range(0, len(PROMPTS), 2):
        cols = st.columns(2)
        for i, prompt in enumerate(PROMPTS[start : start + 2]):
            if cols[i].button(prompt, key=f"ask_prompt_{start}_{i}", use_container_width=True):
                st.session_state.ask_looplens_pending = prompt

    st.markdown('<div class="ask-panel">', unsafe_allow_html=True)
    st.markdown("### Ask your own question")
    st.caption("Type a question in plain language. Common demo questions are answered locally from the loaded records.")
    with st.form("ask_looplens_form", clear_on_submit=True):
        typed_question = st.text_input(
            "Type your question",
            placeholder="Example: Show me the top 10 loops by review score",
        )
        submitted = st.form_submit_button("Ask LoopLens")
    st.markdown("</div>", unsafe_allow_html=True)

    prompt = st.session_state.pop("ask_looplens_pending", None)
    if submitted and typed_question.strip():
        prompt = typed_question.strip()

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = load_memory("looplens-default")

    st.markdown("### Conversation")
    for msg in st.session_state.chat_messages:
        role = msg.get("role", "assistant")
        with st.chat_message(role):
            if role == "assistant":
                if all(k in msg for k in ("intent", "chart", "data")):
                    render_chat_response(msg)
                else:
                    st.markdown(msg.get("content", ""))
            else:
                st.write(msg.get("content", ""))

    bottom_prompt = st.chat_input("Ask another question about the loop data...")
    if bottom_prompt:
        prompt = bottom_prompt
    if not prompt:
        return

    user_msg = {"role": "user", "content": prompt}
    st.session_state.chat_messages.append(user_msg)
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        response = handle_prompt(prompt, data_context, selected_loop_id=selected_loop_id, demo_mode=demo_mode)
        render_chat_response(response)
    st.session_state.chat_messages.append(response)
    save_memory("looplens-default", [{"role": m.get("role", ""), "content": m.get("content", "")} for m in st.session_state.chat_messages])
