from __future__ import annotations

from typing import Any

import polars as pl


FLOW = ["score_total_flow", "total_flow", "total_flow_allyears", "total_flow_window"]
BOTTLENECK = ["score_bottleneck", "bottleneck_amt", "bottleneck_allyears", "bottleneck_window"]
GOVT = ["loop_max_govt_share_pct", "score_govt_share_pct", "max_govt_share_pct"]
OVERHEAD = ["loop_max_strict_overhead_pct", "loop_max_broad_overhead_pct", "score_overhead_pct"]
REPEAT = ["max_participant_loop_count", "score_repeat_loops", "charity_total_loops"]
SAME_YEAR = ["same_year", "score_same_year"]


def val(row: dict[str, Any], names: list[str], default: Any = None) -> Any:
    for name in names:
        x = row.get(name)
        if x not in (None, "", "nan", "NaN"):
            return x
    return default


def num(x: Any) -> float:
    if x in (None, "", "nan", "NaN"):
        return 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def pct_value(x: Any) -> float:
    n = num(x)
    if n > 1:
        return min(n, 100.0)
    return min(n * 100.0, 100.0)


def amount_points(x: Any, max_points: float) -> float:
    n = max(num(x), 0.0)
    if n <= 0:
        return 0.0
    # Hackathon-friendly scale: 1M reaches full points, lower amounts scale linearly.
    return min(n / 1_000_000.0, 1.0) * max_points


def repeat_points(x: Any) -> float:
    n = max(num(x), 0.0)
    if n <= 1:
        return 0.0
    return min((n - 1.0) / 4.0, 1.0) * 10.0


def bool_points(x: Any) -> float:
    if isinstance(x, bool):
        return 10.0 if x else 0.0
    if str(x).strip().lower() in {"1", "true", "yes", "y"}:
        return 10.0
    return min(max(num(x), 0.0), 1.0) * 10.0


def label(score: float) -> str:
    if score >= 65:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def why(row: dict[str, Any]) -> str:
    reasons: list[str] = []
    if num(val(row, FLOW)) > 0:
        reasons.append("circular flow amount")
    if num(val(row, BOTTLENECK)) > 0:
        reasons.append("bottleneck amount")
    if num(val(row, GOVT)) > 0:
        reasons.append("government funding exposure")
    if num(val(row, OVERHEAD)) > 0:
        reasons.append("overhead context")
    if num(val(row, REPEAT)) > 1:
        reasons.append("repeated loop participation")
    if bool_points(val(row, SAME_YEAR)) > 0:
        reasons.append("same-year circular transfer")
    return "Review-priority signal based on " + ", ".join(reasons) if reasons else "Low evidence review-priority signal."


def score_one(row: dict[str, Any]) -> dict[str, Any]:
    flow = amount_points(val(row, FLOW), 25.0)
    bottleneck = amount_points(val(row, BOTTLENECK), 20.0)
    govt = pct_value(val(row, GOVT)) / 100.0 * 20.0
    overhead = pct_value(val(row, OVERHEAD)) / 100.0 * 15.0
    repeat = repeat_points(val(row, REPEAT))
    same_year = bool_points(val(row, SAME_YEAR))
    score = round(min(flow + bottleneck + govt + overhead + repeat + same_year, 100.0), 1)
    return {"review_score": score, "review_label": label(score), "why_flagged": why(row)}


def score_loops(loops: pl.DataFrame, people: pl.DataFrame | None = None) -> pl.DataFrame:
    if loops.is_empty():
        return loops.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("review_score"),
            pl.lit(None, dtype=pl.Utf8).alias("review_label"),
            pl.lit(None, dtype=pl.Utf8).alias("why_flagged"),
        )

    rows = loops.to_dicts()
    scored = [score_one(row) for row in rows]
    out = pl.DataFrame(scored)
    return pl.concat([loops, out], how="horizontal").sort("review_score", descending=True)
