from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pandas as pd

from src.data import TableInfo


BLOCKED = re.compile(
    r"\b(drop|delete|update|insert|alter|create|copy|export|attach|detach|pragma|call|execute|shell)\b",
    re.I,
)


def connect(tables: dict[str, TableInfo]) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database=":memory:")
    for name, info in tables.items():
        path = str(info.path).replace("'", "''")
        ext = info.path.suffix.lower()
        if ext == ".parquet":
            con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}')")
        elif ext == ".csv":
            con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_csv_auto('{path}')")
        elif ext in {".jsonl", ".ndjson"}:
            con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_json_auto('{path}', format='newline_delimited')")
    return con


def schema_text(tables: dict[str, TableInfo]) -> str:
    lines = []
    for name, info in tables.items():
        cols = ", ".join(info.columns)
        lines.append(f"{name}: {cols}")
    return "\n".join(lines)


def ensure_limit(sql: str, limit: int = 50) -> str:
    sql = sql.strip().rstrip(";")
    if re.search(r"\blimit\s+\d+\b", sql, re.I):
        return sql
    return f"{sql} LIMIT {int(limit)}"


def validate(sql: str, tables: dict[str, TableInfo], limit: int = 50) -> tuple[bool, str, str]:
    raw = (sql or "").strip()
    if not raw:
        return False, "", "No SQL was produced."
    if ";" in raw.rstrip(";"):
        return False, "", "Only one SELECT statement is allowed."
    if BLOCKED.search(raw):
        return False, "", "The SQL used a blocked operation."
    if not re.match(r"^\s*(select|with)\b", raw, re.I):
        return False, "", "Only SELECT queries are allowed."
    known_tables = set(tables)
    found_tables = set(re.findall(r"\bfrom\s+([A-Za-z_][A-Za-z0-9_]*)|\bjoin\s+([A-Za-z_][A-Za-z0-9_]*)", raw, re.I))
    flat = {x for pair in found_tables for x in pair if x}
    unknown = sorted(t for t in flat if t not in known_tables)
    if unknown:
        return False, "", f"Unknown table: {', '.join(unknown)}."
    known_cols = {c for info in tables.values() for c in info.columns}
    aliases = set(re.findall(r"\bas\s+\"?([A-Za-z_][A-Za-z0-9_]*)\"?", raw, re.I))
    quoted = set(re.findall(r'"([^"]+)"', raw))
    bad_cols = sorted(x for x in quoted if x not in known_cols and x not in aliases and x not in known_tables)
    if bad_cols:
        return False, "", f"Unknown column: {', '.join(bad_cols)}."
    return True, ensure_limit(raw, limit), ""


def run(con: duckdb.DuckDBPyConnection, sql: str) -> tuple[pd.DataFrame, str | None]:
    try:
        return con.execute(sql).df(), None
    except Exception as exc:
        return pd.DataFrame(), str(exc)
