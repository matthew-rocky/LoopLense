from __future__ import annotations

from pathlib import Path

import polars as pl


ROOT = Path(__file__).resolve().parents[1]
DATASETS = ["cra", "fed", "ab", "general"]
OUT = ROOT / "data" / "processed" / "dataset_inventory.csv"
EXTS = {".jsonl", ".ndjson", ".csv", ".parquet"}


def say(x: object = "") -> None:
    text = str(x)
    print(text.encode("cp1252", errors="replace").decode("cp1252"))


def preview(path: Path) -> tuple[list[str], pl.DataFrame | None, str | None]:
    try:
        if path.suffix in {".jsonl", ".ndjson"}:
            df = pl.read_ndjson(path, n_rows=5)
        elif path.suffix == ".csv":
            df = pl.read_csv(path, n_rows=5, infer_schema_length=100)
        elif path.suffix == ".parquet":
            df = pl.read_parquet(path, n_rows=5)
        else:
            return [], None, "unsupported file type"
        return df.columns, df, None
    except Exception as exc:
        return [], None, str(exc)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str | float]] = []

    for dataset in DATASETS:
        folder = ROOT / dataset
        if not folder.exists():
            say(f"\n{dataset}: missing")
            continue
        say(f"\n=== {dataset} ===")
        for path in sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in EXTS):
            size_mb = path.stat().st_size / (1024 * 1024)
            cols, df, err = preview(path)
            say(f"\n{path.name}")
            say(f"path: {path}")
            say(f"size_mb: {size_mb:.2f}")
            if err:
                say(f"preview_error: {err}")
            else:
                say(f"columns: {cols}")
                say(df)
            rows.append(
                {
                    "dataset": dataset,
                    "file_name": path.name,
                    "path": str(path),
                    "size_mb": round(size_mb, 3),
                    "columns": "|".join(cols),
                    "preview_error": err or "",
                }
            )

    pl.DataFrame(rows).write_csv(OUT)
    say(f"\nSaved inventory to {OUT}")


if __name__ == "__main__":
    main()
