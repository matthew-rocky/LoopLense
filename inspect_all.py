from pathlib import Path
import polars as pl

ROOT = Path(r"C:\AI-Hackathon\Main")

DATASETS = ["cra", "fed", "ab", "general"]
SUPPORTED = {".jsonl", ".ndjson", ".csv", ".parquet"}

for dataset in DATASETS:
    folder = ROOT / dataset

    print("\n" + "=" * 100)
    print(f"DATASET: {dataset}")
    print("=" * 100)

    if not folder.exists():
        print(f"Folder not found: {folder}")
        continue

    files = [
        f for f in folder.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED
    ]

    print(f"Found {len(files)} supported files")

    for file in files[:10]:
        print("\n" + "-" * 100)
        print(f"File: {file}")
        print(f"Size: {file.stat().st_size / 1024 / 1024:.2f} MB")

        try:
            suffix = file.suffix.lower()

            if suffix in [".jsonl", ".ndjson"]:
                df = pl.read_ndjson(file, n_rows=5)
            elif suffix == ".csv":
                df = pl.read_csv(file, n_rows=5, infer_schema_length=1000)
            elif suffix == ".parquet":
                df = pl.read_parquet(file, n_rows=5)
            else:
                continue

            print("Columns:")
            print(df.columns)

            print("Preview:")
            print(df)

        except Exception as e:
            print(f"Could not preview: {e}")