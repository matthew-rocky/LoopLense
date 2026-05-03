from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import polars as pl


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
KINDS = {
    "edges": ["edge", "transfer"],
    "people": ["people", "participant"],
    "profiles": ["profile", "charity_profiles"],
    "inventory": ["inventory"],
    "loops": ["loops_ranked", "ranked", "cycle", "loop"],
}


@dataclass(frozen=True)
class TableInfo:
    name: str
    path: Path
    columns: list[str]
    kind: str
    rows: int | None = None


def _kind(path: Path) -> str:
    low = path.stem.lower()
    if "edge" in low:
        return "edges"
    if "people" in low or "participant" in low:
        return "people"
    if "profile" in low:
        return "profiles"
    if "inventory" in low:
        return "inventory"
    if "loop" in low or "cycle" in low or "ranked" in low:
        return "loops"
    for kind, words in KINDS.items():
        if any(word in low for word in words):
            return kind
    return path.stem.lower()


def _scan(path: Path) -> tuple[list[str], int | None]:
    try:
        if path.suffix.lower() == ".parquet":
            df = pl.scan_parquet(path)
            return df.collect_schema().names(), df.select(pl.len()).collect().item()
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path, nrows=25)
            return list(df.columns), None
        if path.suffix.lower() in {".jsonl", ".ndjson"}:
            df = pd.read_json(path, lines=True, nrows=25)
            return list(df.columns), None
    except Exception:
        return [], None
    return [], None


def discover() -> dict[str, TableInfo]:
    tables: dict[str, TableInfo] = {}
    if not PROCESSED.exists():
        return tables
    used: set[str] = set()
    for path in sorted(PROCESSED.rglob("*")):
        if path.suffix.lower() not in {".parquet", ".csv", ".jsonl", ".ndjson"}:
            continue
        cols, rows = _scan(path)
        if not cols:
            continue
        base = _kind(path)
        name = base
        if name in used:
            name = path.stem.lower().replace("-", "_")
        i = 2
        while name in used:
            name = f"{base}_{i}"
            i += 1
        used.add(name)
        tables[name] = TableInfo(name=name, path=path, columns=cols, kind=base, rows=rows)
    return tables


def preferred(tables: dict[str, TableInfo], kind: str) -> str | None:
    for name, info in tables.items():
        if info.kind == kind and info.path.suffix.lower() == ".parquet":
            return name
    for name, info in tables.items():
        if info.kind == kind:
            return name
    return None


def load_frame(info: TableInfo, limit: int | None = None) -> pd.DataFrame:
    try:
        if info.path.suffix.lower() == ".parquet":
            df = pd.read_parquet(info.path)
        elif info.path.suffix.lower() == ".csv":
            df = pd.read_csv(info.path)
        else:
            df = pd.read_json(info.path, lines=True)
        return df.head(limit) if limit else df
    except Exception:
        return pd.DataFrame()


def find_col(cols: list[str], names: list[str], contains: list[str] | None = None) -> str | None:
    low = {c.lower(): c for c in cols}
    for name in names:
        if name.lower() in low:
            return low[name.lower()]
    for col in cols:
        cl = col.lower()
        if contains and any(part in cl for part in contains):
            return col
    return None


def row_id(row: dict[str, Any]) -> str:
    for name in ("loop_id", "cycle_id", "id", "component_id"):
        if row.get(name) not in (None, ""):
            return str(row[name])
    return ""
