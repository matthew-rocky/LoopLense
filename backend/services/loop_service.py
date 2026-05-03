from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import polars as pl

from src.data import discover
from src.load import PROCESSED, get_edges, get_loop, get_people, load_edges, load_loops, load_people, load_profiles
from src.query import connect
from src.score import score_one

from backend.services.name_service import get_display_name, get_identity_metadata


ID_COLUMNS = ("loop_id", "cycle_id", "id", "component_id")
FLOW_COLUMNS = ("total_flow", "score_total_flow", "total_flow_allyears", "total_flow_window", "bottleneck_amt")
BN_COLUMNS = ("bn", "BN", "charity_bn", "business_number")
SEND_COLUMNS = ("sends_to", "to_bn", "target_bn", "donee_bn", "dst")
RECEIVE_COLUMNS = ("receives_from", "from_bn", "source_bn", "donor_bn", "src")


def clean_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_value(v) for v in value]
    if isinstance(value, tuple):
        return [clean_value(v) for v in value]
    if hasattr(value, "item"):
        try:
            return clean_value(value.item())
        except Exception:
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def records(df: pl.DataFrame) -> list[dict[str, Any]]:
    return [clean_value(row) for row in df.to_dicts()] if not df.is_empty() else []


def loop_id(row: dict[str, Any]) -> str:
    for col in ID_COLUMNS:
        value = row.get(col)
        if value not in (None, ""):
            return str(value)
    return ""


def numeric(value: Any) -> float | None:
    if value in (None, "", "nan", "NaN"):
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(n) or math.isinf(n) else n


def first_col(df: pl.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def first_value(row: dict[str, Any], candidates: tuple[str, ...]) -> Any:
    for name in candidates:
        value = row.get(name)
        if value not in (None, ""):
            return value
    return None


@lru_cache(maxsize=1)
def data_store() -> dict[str, Any]:
    tables = discover()
    return {
        "loops": load_loops(),
        "edges": load_edges(),
        "people": load_people(),
        "profiles": load_profiles(),
        "tables": tables,
        "con": connect(tables),
    }


def health() -> dict[str, Any]:
    expected = {
        "loops": PROCESSED / "loops_ranked.parquet",
        "edges": PROCESSED / "loop_edges.parquet",
        "people": PROCESSED / "people.parquet",
        "profiles": PROCESSED / "charity_profiles.parquet",
    }
    store = data_store()
    return {
        "status": "ok" if expected["loops"].exists() else "missing_data",
        "project": "LoopLens",
        "data_dir": str(PROCESSED),
        "files": {name: {"path": str(path), "found": path.exists()} for name, path in expected.items()},
        "tables": {
            name: {"kind": info.kind, "rows": info.rows, "columns": info.columns, "path": str(info.path)}
            for name, info in store["tables"].items()
        },
    }


def summary() -> dict[str, Any]:
    store = data_store()
    loops: pl.DataFrame = store["loops"]
    edges: pl.DataFrame = store["edges"]
    people: pl.DataFrame = store["people"]
    flow = first_col(loops, FLOW_COLUMNS)
    total_flow = None
    if flow and not loops.is_empty():
        total_flow = loops.select(pl.col(flow).cast(pl.Float64, strict=False).sum()).item()
    label_distribution: list[dict[str, Any]] = []
    if "review_label" in loops.columns and not loops.is_empty():
        label_distribution = records(loops.group_by("review_label").len().rename({"len": "count"}).sort("count", descending=True))
    high = 0
    if "review_label" in loops.columns and not loops.is_empty():
        high = loops.filter(pl.col("review_label") == "High").height
    bn_col = first_col(people, ("bn", "charity_bn", "business_number"))
    total_entities = people.select(pl.col(bn_col).n_unique()).item() if bn_col and not people.is_empty() else 0
    top = loops.sort("review_score", descending=True).head(8) if "review_score" in loops.columns and not loops.is_empty() else loops.head(8)
    return clean_value(
        {
            "total_loops": loops.height,
            "total_edges": edges.height,
            "total_charities_entities": total_entities,
            "high_priority_loops": high,
            "total_circular_flow": total_flow,
            "review_label_distribution": label_distribution,
            "top_high_priority_loops": [enrich_loop(row) for row in records(top)],
            "flow_column": flow,
        }
    )


@lru_cache(maxsize=1)
def people_by_loop() -> dict[str, list[dict[str, Any]]]:
    people: pl.DataFrame = data_store()["people"]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for person in records(people):
        lid = str(first_value(person, ID_COLUMNS) or "")
        if not lid:
            continue
        grouped.setdefault(lid, []).append(enrich_participant(person))
    return grouped


def enrich_participant(person: dict[str, Any]) -> dict[str, Any]:
    row = clean_value(dict(person))
    bn = str(first_value(row, BN_COLUMNS) or "")
    meta = get_identity_metadata(bn)
    sends_to_bn = first_value(row, SEND_COLUMNS)
    receives_from_bn = first_value(row, RECEIVE_COLUMNS)
    name = get_display_name(bn)
    row.update(
        {
            "bn": bn,
            "name": name,
            "organization_name": name,
            "legal_name": row.get("legal_name") or meta.get("legal_name"),
            "account_name": row.get("account_name") or meta.get("account_name"),
            "city": row.get("city") or meta.get("city"),
            "province": row.get("province") or meta.get("province"),
            "postal_code": row.get("postal_code") or meta.get("postal_code"),
            "country": row.get("country") or meta.get("country"),
            "sends_to_bn": str(sends_to_bn) if sends_to_bn not in (None, "") else None,
            "receives_from_bn": str(receives_from_bn) if receives_from_bn not in (None, "") else None,
            "sends_to": get_display_name(str(sends_to_bn)) if sends_to_bn not in (None, "") else None,
            "receives_from": get_display_name(str(receives_from_bn)) if receives_from_bn not in (None, "") else None,
        }
    )
    return row


def enrich_edge(edge: dict[str, Any]) -> dict[str, Any]:
    row = clean_value(dict(edge))
    source_bn = first_value(row, ("src", "from_bn", "source_bn", "donor_bn", "from_charity_bn", "source"))
    target_bn = first_value(row, ("dst", "to_bn", "target_bn", "donee_bn", "to_charity_bn", "target"))
    if source_bn not in (None, ""):
        row["source_bn"] = str(source_bn)
        row["source_name"] = get_display_name(str(source_bn))
        row["src_name"] = row["source_name"]
    if target_bn not in (None, ""):
        row["target_bn"] = str(target_bn)
        row["target_name"] = get_display_name(str(target_bn))
        row["dst_name"] = row["target_name"]
    return row


def participant_rows(loop_id_value: str) -> list[dict[str, Any]]:
    indexed = people_by_loop().get(str(loop_id_value))
    if indexed is not None:
        return indexed
    return [enrich_participant(row) for row in get_people(loop_id_value, data_store()["people"])]


def enrich_loop(row: dict[str, Any], participants: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    out = clean_value(dict(row))
    lid = loop_id(out)
    people = participants if participants is not None else participant_rows(lid)
    flow_value = first_value(out, FLOW_COLUMNS)
    names = [str(person.get("name")) for person in people if person.get("name")]
    out.update(
        {
            "loop_id": lid,
            "label": out.get("review_label"),
            "score": out.get("review_score"),
            "circular_flow": numeric(flow_value),
            "participant_count": out.get("participant_count") or len(people),
            "participant_names": names,
            "participants": people,
        }
    )
    return out


def matches_search(row: dict[str, Any], needle: str) -> bool:
    haystack = " ".join(
        [
            str(row.get("loop_id", "")),
            str(row.get("id", "")),
            str(row.get("review_label", "")),
            str(row.get("why_flagged", "")),
            " ".join(str(name) for name in row.get("participant_names", [])),
            " ".join(str(p.get("bn", "")) for p in row.get("participants", []) if isinstance(p, dict)),
            " ".join(str(p.get("legal_name", "")) for p in row.get("participants", []) if isinstance(p, dict)),
            " ".join(str(p.get("account_name", "")) for p in row.get("participants", []) if isinstance(p, dict)),
        ]
    ).lower()
    return needle in haystack


def list_loops(
    label: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    min_flow: float | None = None,
    limit: int = 100,
    search: str | None = None,
) -> list[dict[str, Any]]:
    loops: pl.DataFrame = data_store()["loops"]
    if loops.is_empty():
        return []
    out = loops
    if label and "review_label" in out.columns:
        labels = [x.strip() for x in label.split(",") if x.strip()]
        out = out.filter(pl.col("review_label").is_in(labels))
    if min_score is not None and "review_score" in out.columns:
        out = out.filter(pl.col("review_score").cast(pl.Float64, strict=False).fill_null(0) >= min_score)
    if max_score is not None and "review_score" in out.columns:
        out = out.filter(pl.col("review_score").cast(pl.Float64, strict=False).fill_null(0) <= max_score)
    flow = first_col(out, FLOW_COLUMNS)
    if min_flow is not None and flow:
        out = out.filter(pl.col(flow).cast(pl.Float64, strict=False).fill_null(0) >= min_flow)
    if "review_score" in out.columns:
        out = out.sort("review_score", descending=True)
    max_rows = max(1, min(limit, 1000))
    if search:
        enriched = [enrich_loop(row) for row in records(out)]
        needle = search.lower().strip()
        enriched = [row for row in enriched if matches_search(row, needle)]
    else:
        enriched = [enrich_loop(row) for row in records(out.head(max_rows))]
    return enriched[:max_rows]


def loop_detail(loop_id_value: str) -> dict[str, Any]:
    store = data_store()
    loop = clean_value(get_loop(loop_id_value, store["loops"]))
    people = participant_rows(loop_id_value)
    loop = enrich_loop(loop, people) if loop else {}
    edges = [enrich_edge(edge) for edge in get_edges(loop_id_value, store["edges"])]
    explanation = score_one(loop) if loop else {}
    return {
        "loop": loop,
        "edges": edges,
        "people": people,
        "score_explanation": {
            "review_score": loop.get("review_score") if loop else explanation.get("review_score"),
            "review_label": loop.get("review_label") if loop else explanation.get("review_label"),
            "why_flagged": loop.get("why_flagged") if loop else explanation.get("why_flagged"),
            "computed": explanation,
        },
    }


def selected_context(loop_id_value: str | None) -> dict[str, Any]:
    store = data_store()
    selected = {}
    selected_edges: list[dict[str, Any]] = []
    selected_people: list[dict[str, Any]] = []
    selected_id = loop_id_value
    if selected_id:
        detail = loop_detail(selected_id)
        selected = detail["loop"]
        selected_edges = detail["edges"]
        selected_people = detail["people"]
    elif not store["loops"].is_empty():
        selected = enrich_loop(records(store["loops"].sort("review_score", descending=True).head(1))[0])
        selected_id = loop_id(selected)
        selected_edges = [enrich_edge(edge) for edge in get_edges(selected_id, store["edges"])]
        selected_people = participant_rows(selected_id)
    return {
        "tables": store["tables"],
        "con": store["con"],
        "selected_loop": selected,
        "selected_loop_id": selected_id,
        "selected_edges": selected_edges,
        "selected_people": selected_people,
    }


def data_file_paths() -> list[Path]:
    return list(PROCESSED.glob("*"))
