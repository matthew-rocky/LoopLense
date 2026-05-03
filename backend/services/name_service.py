from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import polars as pl


ROOT = Path(__file__).resolve().parents[2]
CRA = ROOT / "cra"


def _text(value: Any) -> str:
    if value in (None, "", "nan", "NaN"):
        return ""
    return str(value).strip()


def _year(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return -1


def _read_jsonl(path: Path, columns: list[str]) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    try:
        available = pl.scan_ndjson(path).collect_schema().names()
        selected = [col for col in columns if col in available]
        if not selected:
            return []
        return pl.scan_ndjson(path).select(selected).collect().to_dicts()
    except Exception:
        return []


def _keep_latest(target: dict[str, tuple[int, str]], bn: str, year: int, value: str) -> None:
    if not bn or not value:
        return
    current = target.get(bn)
    if current is None or year > current[0]:
        target[bn] = (year, value)


@lru_cache(maxsize=1)
def build_bn_name_map() -> dict[str, str]:
    names = _name_data()
    return dict(names["display_names"])


@lru_cache(maxsize=1)
def _name_data() -> dict[str, Any]:
    history_legal: dict[str, tuple[int, str]] = {}
    history_account: dict[str, tuple[int, str]] = {}
    cra_legal: dict[str, tuple[int, str]] = {}
    cra_account: dict[str, tuple[int, str]] = {}
    metadata: dict[str, dict[str, Any]] = {}

    for row in _read_jsonl(CRA / "identification_name_history.jsonl", ["bn", "legal_name", "account_name", "last_year"]):
        bn = _text(row.get("bn"))
        year = _year(row.get("last_year"))
        _keep_latest(history_legal, bn, year, _text(row.get("legal_name")))
        _keep_latest(history_account, bn, year, _text(row.get("account_name")))

    for row in _read_jsonl(
        CRA / "cra_identification.jsonl",
        ["bn", "fiscal_year", "legal_name", "account_name", "city", "province", "postal_code", "country", "category", "designation"],
    ):
        bn = _text(row.get("bn"))
        year = _year(row.get("fiscal_year"))
        _keep_latest(cra_legal, bn, year, _text(row.get("legal_name")))
        _keep_latest(cra_account, bn, year, _text(row.get("account_name")))
        current = metadata.get(bn)
        if bn and (current is None or year > _year(current.get("fiscal_year"))):
            metadata[bn] = {
                "bn": bn,
                "fiscal_year": year if year >= 0 else None,
                "legal_name": _text(row.get("legal_name")) or None,
                "account_name": _text(row.get("account_name")) or None,
                "city": _text(row.get("city")) or None,
                "province": _text(row.get("province")) or None,
                "postal_code": _text(row.get("postal_code")) or None,
                "country": _text(row.get("country")) or None,
                "category": _text(row.get("category")) or None,
                "designation": _text(row.get("designation")) or None,
            }

    display_names: dict[str, str] = {}
    for source in (history_legal, history_account, cra_legal, cra_account):
        for bn, (_year_value, name) in source.items():
            display_names.setdefault(bn, name)

    return {"display_names": display_names, "metadata": metadata}


def get_display_name(bn: str) -> str:
    normalized = _text(bn)
    if not normalized:
        return ""
    return build_bn_name_map().get(normalized, normalized)


def get_identity_metadata(bn: str) -> dict[str, Any]:
    normalized = _text(bn)
    meta = dict(_name_data()["metadata"].get(normalized, {}))
    meta.setdefault("bn", normalized)
    meta.setdefault("name", get_display_name(normalized))
    return meta
