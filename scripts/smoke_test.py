from __future__ import annotations

import json
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.memo import make_memo
from src.score import score_loops
from src.verify import build_memo


def main() -> None:
    loop = {
        "loop_id": "demo-loop-1",
        "participant_count": 3,
        "total_flow": 125000,
        "bottleneck_amt": 42000,
        "loop_max_govt_share_pct": 0.63,
        "loop_max_strict_overhead_pct": 0.18,
        "same_year": True,
        "max_participant_loop_count": 3,
    }
    edges = [
        {"loop_id": "demo-loop-1", "from_bn": "100000001", "to_bn": "100000002", "amount": 50000, "year": 2022},
        {"loop_id": "demo-loop-1", "from_bn": "100000002", "to_bn": "100000003", "amount": 42000, "year": 2022},
        {"loop_id": "demo-loop-1", "from_bn": "100000003", "to_bn": "100000001", "amount": 33000, "year": 2022},
    ]
    people = [
        {"loop_id": "demo-loop-1", "bn": "100000001", "charity_name": "North Program Foundation"},
        {"loop_id": "demo-loop-1", "bn": "100000002", "charity_name": "Civic Learning Trust"},
        {"loop_id": "demo-loop-1", "bn": "100000003", "charity_name": "Community Arts Fund"},
    ]
    scored = score_loops(pl.DataFrame([loop]))
    memo = make_memo(loop, edges, people, use_llm=False)
    result = build_memo(loop, edges, people, use_llm=False)
    print("Scored loop:")
    print(json.dumps(scored.to_dicts(), indent=2))
    print("\nFallback memo:")
    print(json.dumps(memo, indent=2))
    print("\nVerified memo:")
    print(json.dumps(result, indent=2))
    print("\nSmoke test passed")


if __name__ == "__main__":
    main()
