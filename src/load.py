from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def _empty() -> pl.DataFrame:
    return pl.DataFrame()


def _read(name: str) -> pl.DataFrame:
    path = PROCESSED / name
    if not path.exists():
        return _empty()
    try:
        return pl.read_parquet(path)
    except Exception:
        return _empty()


def load_loops() -> pl.DataFrame:
    return _read("loops_ranked.parquet")


def load_edges() -> pl.DataFrame:
    return _read("loop_edges.parquet")


def load_people() -> pl.DataFrame:
    return _read("people.parquet")


def load_profiles() -> pl.DataFrame:
    return _read("charity_profiles.parquet")


def _id(row: dict[str, Any]) -> str:
    for name in ("loop_id", "cycle_id", "id", "component_id"):
        if row.get(name) not in (None, ""):
            return str(row[name])
    return ""


def get_loop(loop_id: Any, loops: pl.DataFrame) -> dict[str, Any]:
    if loops.is_empty():
        return {}
    wanted = str(loop_id)
    for row in loops.to_dicts():
        if _id(row) == wanted:
            return row
    return loops.row(0, named=True)


def _filter(loop_id: Any, df: pl.DataFrame) -> list[dict[str, Any]]:
    if df.is_empty():
        return []
    cols = [c for c in ("loop_id", "cycle_id", "id", "component_id") if c in df.columns]
    if not cols:
        return df.head(100).to_dicts()
    wanted = str(loop_id)
    expr = None
    for col in cols:
        part = pl.col(col).cast(pl.Utf8) == wanted
        expr = part if expr is None else expr | part
    return df.filter(expr).head(500).to_dicts()


def get_edges(loop_id: Any, edges: pl.DataFrame) -> list[dict[str, Any]]:
    return _filter(loop_id, edges)


def get_people(loop_id: Any, people: pl.DataFrame) -> list[dict[str, Any]]:
    return _filter(loop_id, people)
