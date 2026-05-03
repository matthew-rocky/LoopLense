from __future__ import annotations

from typing import Any


def _get(row: dict[str, Any], *names: str, default: Any = "") -> Any:
    for name in names:
        if row.get(name) not in (None, ""):
            return row[name]
    return default


def edge_table(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for edge in edges:
        rows.append(
            {
                "from": _get(edge, "from_bn", "source_bn", "donor_bn", "from_charity_bn", "source"),
                "to": _get(edge, "to_bn", "target_bn", "donee_bn", "to_charity_bn", "target"),
                "amount": _get(edge, "amount", "total_amount", "flow_amount", "transfer_amount", "amt"),
                "year": _get(edge, "year", "fiscal_year", "period"),
            }
        )
        rows[-1]["from"] = rows[-1]["from"] or _get(edge, "src")
        rows[-1]["to"] = rows[-1]["to"] or _get(edge, "dst")
        rows[-1]["amount"] = rows[-1]["amount"] or _get(edge, "total_amt")
        rows[-1]["year"] = rows[-1]["year"] or _get(edge, "min_year", "max_year", "years")
    return rows
