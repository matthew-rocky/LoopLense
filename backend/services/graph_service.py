from __future__ import annotations

from typing import Any

from backend.services.loop_service import clean_value, loop_detail
from backend.services.name_service import get_display_name, get_identity_metadata


def _get(row: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    return default


def _person_label(bn: str, people: list[dict[str, Any]]) -> str:
    for person in people:
        pbn = str(_get(person, "bn", "BN", "charity_bn", "business_number", default=""))
        if pbn == str(bn):
            return str(_get(person, "name", "organization_name", "legal_name", "account_name", "charity_name", default=get_display_name(bn)))
    return get_display_name(bn)


def _num(value: Any) -> float:
    if value in (None, "", "nan", "NaN"):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _years(value: Any, min_year: Any = None, max_year: Any = None) -> list[int]:
    years: list[int] = []
    if isinstance(value, list):
        years = [year for year in (_int(item) for item in value) if year is not None]
    elif isinstance(value, str):
        cleaned = value.strip().strip("[]")
        for part in cleaned.replace(";", ",").split(","):
            year = _int(part.strip())
            if year is not None:
                years.append(year)
    if not years:
        start = _int(min_year)
        end = _int(max_year)
        if start is not None and end is not None:
            years = list(range(start, end + 1))
        elif start is not None:
            years = [start]
        elif end is not None:
            years = [end]
    return sorted(set(years))


def _edge_source(edge: dict[str, Any]) -> str:
    return str(_get(edge, "src", "from_bn", "source_bn", "donor_bn", "from_charity_bn", "source", default=""))


def _edge_target(edge: dict[str, Any]) -> str:
    return str(_get(edge, "dst", "to_bn", "target_bn", "donee_bn", "to_charity_bn", "target", default=""))


def _edge_amount(edge: dict[str, Any]) -> float:
    return _num(_get(edge, "total_amt", "amount", "total_amount", "flow_amount", "transfer_amount", "amt", default=0))


def _person(node_id: str, people: list[dict[str, Any]]) -> dict[str, Any]:
    return next((p for p in people if str(_get(p, "bn", "charity_bn", "business_number", default="")) == node_id), {})


def network(loop_id: str) -> dict[str, Any]:
    detail = loop_detail(loop_id)
    loop = detail["loop"]
    people = detail["people"]
    raw_edges = [edge for edge in detail["edges"] if _edge_source(edge) and _edge_target(edge)]
    participant_ids = [str(_get(person, "bn", "charity_bn", "business_number", default="")) for person in people]
    cycle_ids = [str(item) for item in loop.get("path_bns", [])] if isinstance(loop.get("path_bns"), list) else []
    cycle_pairs = set(zip(cycle_ids, cycle_ids[1:] + cycle_ids[:1])) if cycle_ids else set()
    existing_pairs = {(_edge_source(edge), _edge_target(edge)) for edge in raw_edges}
    inferred_amount = _num(_get(loop, "bottleneck_amt", "score_bottleneck", "circular_flow", "total_flow", default=0))
    inferred_edges: list[dict[str, Any]] = []
    for person in people:
        source = str(_get(person, "bn", "charity_bn", "business_number", default=""))
        target = str(_get(person, "sends_to_bn", "sends_to", default=""))
        if not source or not target or (source, target) in existing_pairs:
            continue
        inferred_edges.append(
            {
                "loop_id": loop_id,
                "src": source,
                "dst": target,
                "total_amt": inferred_amount,
                "edge_count": 1,
                "min_year": loop.get("min_year"),
                "max_year": loop.get("max_year"),
                "years": _years(None, loop.get("min_year"), loop.get("max_year")),
                "evidence_source": "loop_participants",
                "is_inferred": True,
            }
        )

    graph_edges = raw_edges + inferred_edges
    node_ids = list(dict.fromkeys(participant_ids + [_edge_source(edge) for edge in graph_edges] + [_edge_target(edge) for edge in graph_edges]))

    sent = {node_id: 0.0 for node_id in node_ids}
    received = {node_id: 0.0 for node_id in node_ids}
    outgoing = {node_id: 0 for node_id in node_ids}
    incoming = {node_id: 0 for node_id in node_ids}
    for edge in graph_edges:
        source = _edge_source(edge)
        target = _edge_target(edge)
        amount = _edge_amount(edge)
        sent[source] = sent.get(source, 0.0) + amount
        received[target] = received.get(target, 0.0) + amount
        outgoing[source] = outgoing.get(source, 0) + 1
        incoming[target] = incoming.get(target, 0) + 1

    nodes = [
        {
            "id": node_id,
            "label": _person_label(node_id, people),
            "bn": node_id,
            "legal_name": _get(_person(node_id, people), "legal_name", default=get_identity_metadata(node_id).get("legal_name")),
            "account_name": _get(_person(node_id, people), "account_name", default=get_identity_metadata(node_id).get("account_name")),
            "city": _get(_person(node_id, people), "city", default=get_identity_metadata(node_id).get("city")),
            "province": _get(_person(node_id, people), "province", default=get_identity_metadata(node_id).get("province")),
            "position_in_loop": _get(_person(node_id, people), "position_in_loop", default=None),
            "total_sent": round(sent.get(node_id, 0.0), 2),
            "total_received": round(received.get(node_id, 0.0), 2),
            "outgoing_edges": outgoing.get(node_id, 0),
            "incoming_edges": incoming.get(node_id, 0),
            "is_cycle_node": node_id in cycle_ids if cycle_ids else True,
            "type": "charity",
            "metadata": {
                **get_identity_metadata(node_id),
                **_person(node_id, people),
                "bn": node_id,
            },
        }
        for node_id in node_ids
    ]
    edges = [
        {
            "id": f"edge-{idx + 1}",
            "source": _edge_source(edge),
            "target": _edge_target(edge),
            "source_name": get_display_name(_edge_source(edge)),
            "target_name": get_display_name(_edge_target(edge)),
            "amount": round(_edge_amount(edge), 2),
            "edge_count": _int(_get(edge, "edge_count", default=1)) or 1,
            "min_year": _int(_get(edge, "min_year", "year", "fiscal_year", default=None)),
            "max_year": _int(_get(edge, "max_year", "year", "fiscal_year", default=None)),
            "years": _years(edge.get("years"), _get(edge, "min_year", "year"), _get(edge, "max_year", "year")),
            "is_cycle_edge": ((_edge_source(edge), _edge_target(edge)) in cycle_pairs) if cycle_pairs else True,
            "is_inferred": bool(edge.get("is_inferred")),
            "evidence_source": edge.get("evidence_source", "loop_edges"),
            "metadata": edge,
        }
        for idx, edge in enumerate(graph_edges)
    ]
    amounts = [edge["amount"] for edge in edges]
    years = sorted({year for edge in edges for year in edge.get("years", [])})
    summary = {
        "participant_count": loop.get("participant_count") or len(nodes),
        "circular_flow": _num(_get(loop, "circular_flow", "total_flow", "score_total_flow", default=0)),
        "score": _num(_get(loop, "review_score", "score", default=0)),
        "label": _get(loop, "review_label", "label", default="Unscored"),
        "min_year": min(years) if years else _int(loop.get("min_year")),
        "max_year": max(years) if years else _int(loop.get("max_year")),
        "total_edges": len(edges),
        "highest_transfer_edge": max(amounts) if amounts else 0,
    }
    return clean_value(
        {
            "loop_id": str(loop_id),
            "summary": summary,
            "nodes": nodes,
            "edges": edges,
            "highlight_circular_path": cycle_ids or node_ids,
        }
    )
