from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Any

import polars as pl
from polars.exceptions import PolarsInefficientMapWarning
from polars.datatypes import Array, List, Object, Struct

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore", category=PolarsInefficientMapWarning)

from src.score import score_loops


CRA = ROOT / "cra"
OUT = ROOT / "data" / "processed"


def warn(msg: str) -> None:
    print(f"Warning: {msg}")


def read(name: str, n_rows: int | None = None) -> pl.DataFrame:
    path = CRA / name
    if not path.exists() or path.stat().st_size == 0:
        warn(f"{name} not found or empty")
        return pl.DataFrame()
    try:
        if path.suffix in {".jsonl", ".ndjson"}:
            return pl.read_ndjson(path, n_rows=n_rows)
        if path.suffix == ".csv":
            return pl.read_csv(path, n_rows=n_rows)
        if path.suffix == ".parquet":
            return pl.read_parquet(path, n_rows=n_rows)
    except Exception as exc:
        warn(f"could not read {name}: {exc}")
    return pl.DataFrame()


def first_col(df: pl.DataFrame, names: list[str]) -> str | None:
    for name in names:
        if name in df.columns:
            return name
    return None


def cast_key(df: pl.DataFrame, col: str | None) -> pl.DataFrame:
    if not col or col not in df.columns:
        return df
    return df.with_columns(pl.col(col).cast(pl.Utf8).alias(col))


def unique_by(df: pl.DataFrame, col: str | None) -> pl.DataFrame:
    if df.is_empty() or not col or col not in df.columns:
        return df
    return df.unique(subset=[col], keep="first")


def add_loop_id(df: pl.DataFrame) -> pl.DataFrame:
    if df.is_empty():
        return df
    for col in ("loop_id", "cycle_id", "id"):
        if col in df.columns:
            return df.with_columns(pl.col(col).cast(pl.Utf8).alias("loop_id"))
    return df.with_row_index("loop_id").with_columns(pl.col("loop_id").cast(pl.Utf8))


def join_one(left: pl.DataFrame, right: pl.DataFrame, left_names: list[str], right_names: list[str]) -> pl.DataFrame:
    if left.is_empty() or right.is_empty():
        return left
    lcol = first_col(left, left_names)
    rcol = first_col(right, right_names)
    if not lcol or not rcol:
        return left
    left = cast_key(left, lcol)
    right = unique_by(cast_key(right, rcol), rcol)
    try:
        return left.join(right, left_on=lcol, right_on=rcol, how="left", suffix="_profile")
    except Exception as exc:
        warn(f"join skipped on {lcol}/{rcol}: {exc}")
        return left


def build_profiles() -> pl.DataFrame:
    ident = read("cra_identification.jsonl")
    govt = read("govt_funding_by_charity.jsonl")
    overhead = read("overhead_by_charity.jsonl")

    if ident.is_empty():
        profiles = pl.DataFrame()
    else:
        keep = [
            c
            for c in ident.columns
            if c.lower() in {"bn", "business_number", "charity_bn", "account_name", "charity_name", "legal_name", "designation"}
            or "name" in c.lower()
        ]
        profiles = ident.select(keep) if keep else ident

    if not govt.is_empty() and "bn" in govt.columns:
        agg = []
        if "govt_share_of_rev" in govt.columns:
            agg.append(pl.col("govt_share_of_rev").cast(pl.Float64, strict=False).max().alias("max_govt_share_pct"))
        if "total_govt" in govt.columns:
            agg.append(pl.col("total_govt").cast(pl.Float64, strict=False).sum().alias("total_govt_all_years"))
        govt = govt.with_columns(pl.col("bn").cast(pl.Utf8)).group_by("bn").agg(agg) if agg else pl.DataFrame()

    if not overhead.is_empty() and "bn" in overhead.columns:
        agg = []
        if "strict_overhead_pct" in overhead.columns:
            agg.append(pl.col("strict_overhead_pct").cast(pl.Float64, strict=False).max().alias("max_strict_overhead_pct"))
        if "broad_overhead_pct" in overhead.columns:
            agg.append(pl.col("broad_overhead_pct").cast(pl.Float64, strict=False).max().alias("max_broad_overhead_pct"))
        overhead = overhead.with_columns(pl.col("bn").cast(pl.Utf8)).group_by("bn").agg(agg) if agg else pl.DataFrame()

    if profiles.is_empty() and not govt.is_empty():
        profiles = govt
    else:
        profiles = join_one(profiles, govt, ["bn", "business_number", "charity_bn"], ["bn"])

    profiles = join_one(profiles, overhead, ["bn", "business_number", "charity_bn"], ["bn"])
    key = first_col(profiles, ["bn", "business_number", "charity_bn"])
    return unique_by(cast_key(profiles, key), key)


def enrich_people(people: pl.DataFrame, profiles: pl.DataFrame) -> pl.DataFrame:
    if people.is_empty():
        return people
    people = add_loop_id(people)
    return join_one(people, profiles, ["bn", "BN", "charity_bn", "business_number"], ["bn", "business_number", "charity_bn"])


def enrich_loops(loops: pl.DataFrame, people: pl.DataFrame) -> pl.DataFrame:
    loops = add_loop_id(loops)
    if people.is_empty() or "loop_id" not in people.columns:
        return loops
    stats = []
    if first_col(people, ["bn", "BN", "charity_bn", "business_number"]):
        bn = first_col(people, ["bn", "BN", "charity_bn", "business_number"])
        stats.append(pl.col(bn).n_unique().alias("participant_count"))
    for out_name, candidates in {
        "loop_max_govt_share_pct": ["govt_share_pct", "max_govt_share_pct", "score_govt_share_pct"],
        "loop_max_strict_overhead_pct": ["strict_overhead_pct", "max_strict_overhead_pct", "score_overhead_pct"],
        "max_participant_loop_count": ["charity_total_loops", "loop_count", "score_repeat_loops"],
    }.items():
        col = first_col(people, candidates)
        if col:
            stats.append(pl.col(col).cast(pl.Float64, strict=False).max().alias(out_name))
    if not stats:
        return loops
    agg = people.group_by("loop_id").agg(stats)
    return loops.join(agg, on="loop_id", how="left", suffix="_people")


def choose_loops() -> pl.DataFrame:
    for name in ["loops.jsonl", "johnson_cycles.jsonl", "partitioned_cycles.jsonl"]:
        df = read(name)
        if not df.is_empty():
            print(f"Using {name} as loop source")
            return df
    warn("No loop source found. Writing empty processed outputs.")
    return pl.DataFrame()


def csv_safe(df: pl.DataFrame) -> pl.DataFrame:
    exprs = []
    for name, dtype in zip(df.columns, df.dtypes):
        if isinstance(dtype, (Array, List, Object, Struct)):
            exprs.append(pl.col(name).map_elements(lambda x: str(x), return_dtype=pl.Utf8).alias(name))
        else:
            exprs.append(pl.col(name))
    return df.select(exprs)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    loops = choose_loops()
    edges = add_loop_id(read("loop_edges.jsonl"))
    people = read("loop_participants.jsonl")
    profiles = build_profiles()
    people = enrich_people(people, profiles)
    loops = enrich_loops(loops, people)
    ranked = score_loops(loops, people)

    ranked.write_parquet(OUT / "loops_ranked.parquet")
    csv_safe(ranked).write_csv(OUT / "loops_ranked.csv")
    edges.write_parquet(OUT / "loop_edges.parquet")
    people.write_parquet(OUT / "people.parquet")
    profiles.write_parquet(OUT / "charity_profiles.parquet")

    print(f"Wrote {ranked.height} loops to {OUT / 'loops_ranked.parquet'}")
    print(f"Wrote {edges.height} edges to {OUT / 'loop_edges.parquet'}")
    print(f"Wrote {people.height} participant rows to {OUT / 'people.parquet'}")
    print(f"Wrote {profiles.height} charity profiles to {OUT / 'charity_profiles.parquet'}")


if __name__ == "__main__":
    main()
