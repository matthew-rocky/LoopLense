from __future__ import annotations

from typing import Any


BLOCKED_WORDS = [
    "fraud",
    "criminal",
    "illegal",
    "corrupt",
    "corruption",
    "scam",
    "laundering",
]


def clean(text: Any) -> str:
    out = str(text or "")
    replacements = {
        "high risk": "high review priority",
        "suspicious": "may warrant review",
        "scheme": "circular transfer pattern",
        "proof": "indicator",
    }
    for old, new in replacements.items():
        out = out.replace(old, new).replace(old.title(), new.title())
    for word in BLOCKED_WORDS:
        out = out.replace(word, "review concern").replace(word.title(), "Review concern")
    return out


def money(value: Any) -> str:
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "n/a"


def number(value: Any, digits: int = 0) -> str:
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return "n/a"


def score(value: Any) -> str:
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "n/a"


def ratio_indicator(value: Any) -> str:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if 0 <= val <= 1:
        return f"{val * 100:,.1f}%"
    if 1 < val <= 100:
        return f"{val:,.1f}"
    return f"{val:,.2f} ratio indicator"


def friendly_column(name: Any) -> str:
    text = str(name or "").replace("_", " ").strip()
    fixes = {
        "bn": "BN",
        "id": "ID",
        "govt": "government",
        "pct": "indicator",
    }
    words = [fixes.get(part.lower(), part) for part in text.split()]
    return " ".join(words).title().replace("Bn", "BN").replace("Id", "ID")


def short_id(row: dict[str, Any]) -> str:
    for name in ("loop_id", "cycle_id", "id", "component_id"):
        value = row.get(name)
        if value not in (None, ""):
            return str(value)
    return "selected-loop"
