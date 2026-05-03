from __future__ import annotations

import json
import re
from typing import Any

from src.llm import bedrock_ready, converse_text


DISCLAIMER = (
    "This memo is not a finding of wrongdoing. It is an evidence-based "
    "review-priority summary based on available CRA records."
)

BLOCKED = [
    "fraud",
    "corrupt",
    "corruption",
    "illegal",
    "criminal",
    "scam",
    "shell charity",
    "proves misuse",
    "proves wrongdoing",
    "intentional misuse",
    "guilty",
    "laundering",
    "fake charity",
]


def val(row: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in row and row[name] not in (None, "", "nan", "NaN"):
            return row[name]
    return default


def safe_num(x: Any) -> float | None:
    if x in (None, "", "nan", "NaN"):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def num(x: Any) -> float | None:
    return safe_num(x)


def money(x: Any) -> str:
    n = safe_num(x)
    if n is None:
        return "not available"
    return f"${n:,.0f}"


def pct(x: Any) -> str:
    n = safe_num(x)
    if n is None:
        return "not available"
    if n > 100:
        return f"{n:,.2f} ratio indicator"
    if 0 <= n <= 1:
        n *= 100
    return f"{n:.1f}%"


def clean_json(text: str) -> dict[str, Any]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.I).strip()
    text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def _names(people: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for person in people:
        name = val(person, "name", "charity_name", "legal_name", "account_name")
        bn = val(person, "bn", "BN", "charity_bn", "business_number")
        label = str(name or bn or "").strip()
        if label and label not in names:
            names.append(label)
    return names


def _claim(cid: str, text: str, kind: str, fields: list[str]) -> dict[str, Any]:
    return {"id": cid, "text": text, "type": kind, "fields": fields}


def fallback_memo(
    loop: dict[str, Any],
    edges: list[dict[str, Any]],
    people: list[dict[str, Any]],
) -> dict[str, Any]:
    loop_id = val(loop, "loop_id", "id", "cycle_id", default="selected loop")
    count = val(loop, "participant_count", default=len(_names(people)) or None)
    flow = val(loop, "score_total_flow", "total_flow", "total_flow_allyears", "total_flow_window")
    bottleneck = val(loop, "score_bottleneck", "bottleneck_amt", "bottleneck_allyears", "bottleneck_window")
    govt = val(
        loop,
        "loop_max_govt_share_pct",
        "score_govt_share_pct",
        "max_govt_share_pct",
        "avg_govt_share_pct",
    )
    overhead = val(
        loop,
        "loop_max_strict_overhead_pct",
        "loop_max_broad_overhead_pct",
        "score_overhead_pct",
        "max_strict_overhead_pct",
        "max_broad_overhead_pct",
    )
    same_year = val(loop, "same_year", "score_same_year")
    repeat = val(loop, "max_participant_loop_count", "score_repeat_loops", "charity_total_loops")

    names = _names(people)
    named = ", ".join(names[:4])
    if len(names) > 4:
        named += f", and {len(names) - 4} more"

    findings: list[str] = []
    claims: list[dict[str, Any]] = []

    if count is not None:
        text = f"The loop includes {int(safe_num(count) or 0)} participant charities."
        findings.append(text)
        claims.append(_claim("c1", text, "participants", ["participant_count", "participant_bns"]))
    elif names:
        text = f"The selected evidence includes participant records for {len(names)} charities."
        findings.append(text)
        claims.append(_claim("c1", text, "participants", ["people"]))
    else:
        text = "Participant details were not available in the selected evidence."
        findings.append(text)
        claims.append(_claim("c1", text, "participants", ["participant_count", "people"]))

    if flow is not None:
        text = f"The available records show a total circular flow of {money(flow)}."
        findings.append(text)
        claims.append(
            _claim(
                "c2",
                text,
                "flow",
                ["score_total_flow", "total_flow", "total_flow_allyears", "total_flow_window"],
            )
        )

    if bottleneck is not None:
        text = f"The bottleneck amount is {money(bottleneck)}, which helps size the loop's practical review priority."
        findings.append(text)
        claims.append(
            _claim(
                "c3",
                text,
                "bottleneck",
                ["score_bottleneck", "bottleneck_amt", "bottleneck_allyears", "bottleneck_window"],
            )
        )

    if govt is not None:
        text = f"The highest available government funding share tied to the loop is {pct(govt)}."
        findings.append(text)
        claims.append(
            _claim(
                "c4",
                text,
                "govt",
                [
                    "loop_max_govt_share_pct",
                    "score_govt_share_pct",
                    "max_govt_share_pct",
                    "avg_govt_share_pct",
                    "total_govt_all_years",
                ],
            )
        )

    if overhead is not None:
        text = f"The highest available overhead indicator tied to the loop is {pct(overhead)}."
        findings.append(text)
        claims.append(
            _claim(
                "c5",
                text,
                "overhead",
                [
                    "loop_max_strict_overhead_pct",
                    "loop_max_broad_overhead_pct",
                    "score_overhead_pct",
                    "max_strict_overhead_pct",
                    "max_broad_overhead_pct",
                ],
            )
        )

    if same_year not in (None, ""):
        text = "The selected records include a same-year movement indicator for this loop."
        findings.append(text)
        claims.append(_claim("c6", text, "same_year", ["same_year", "score_same_year"]))

    if repeat is not None:
        text = "At least one participant appears in repeated loop indicators in the selected records."
        findings.append(text)
        claims.append(
            _claim(
                "c7",
                text,
                "repeat",
                ["max_participant_loop_count", "score_repeat_loops", "charity_total_loops"],
            )
        )

    if not findings:
        findings.append("The selected loop has limited structured evidence available for memo generation.")
        claims.append(_claim("c1", findings[0], "neutral", []))

    summary = (
        f"LoopLens identified {loop_id} as a review-priority signal based on available CRA records. "
        "The file may merit follow-up review because the selected data describes a circular funding pattern"
        " between registered charities."
    )
    if named:
        summary += f" The participant evidence includes {named}."

    return {
        "title": f"Review-priority memo for {loop_id}",
        "summary": summary,
        "findings": findings,
        "rationale": (
            "The score is produced by deterministic data logic. This memo explains the selected evidence "
            "and does not infer intent or make legal conclusions."
        ),
        "next_steps": [
            "Review the underlying T3010 filings and transfer records for the selected years.",
            "Confirm charity identities and business numbers before drawing conclusions.",
            "Compare the loop against program activity, related-party disclosures, and grant descriptions.",
            "Escalate only if human review finds evidence that requires follow-up.",
        ],
        "disclaimer": DISCLAIMER,
        "claims": claims,
        "source": "fallback",
        "warning": None,
    }


def _pack(loop: dict[str, Any], edges: list[dict[str, Any]], people: list[dict[str, Any]]) -> dict[str, Any]:
    return {"loop": loop, "edges": edges, "people": people}


def _prompt(evidence: dict[str, Any]) -> list[dict[str, str]]:
    system = (
        "You write neutral audit-style charity funding memos. Return valid JSON only. "
        "Do not infer intent, guilt, fraud, illegality, or wrongdoing. Use only facts directly "
        "present in the supplied evidence. Each claim must be verifiable against listed fields. "
        "Avoid unsupported language and blocked terms."
    )
    user = {
        "task": "Write a concise evidence-grounded memo for a circular charity funding loop.",
        "required_keys": [
            "title",
            "summary",
            "findings",
            "rationale",
            "next_steps",
            "disclaimer",
            "claims",
        ],
        "claim_shape": {"id": "c1", "text": "claim text", "type": "flow", "fields": ["field_name"]},
        "allowed_claim_types": [
            "participants",
            "flow",
            "bottleneck",
            "govt",
            "overhead",
            "same_year",
            "repeat",
            "neutral",
        ],
        "required_disclaimer": DISCLAIMER,
        "evidence": evidence,
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, default=str)},
    ]


def llm_memo(
    loop: dict[str, Any],
    edges: list[dict[str, Any]],
    people: list[dict[str, Any]],
) -> dict[str, Any]:
    messages = _prompt(_pack(loop, edges, people))
    system = messages[0]["content"]
    user = messages[1]["content"]
    text = converse_text(
        system + " Return one JSON object only.",
        user,
    )
    memo = clean_json(text)
    memo["source"] = "bedrock"
    memo["warning"] = None
    memo.setdefault("disclaimer", DISCLAIMER)
    memo.setdefault("claims", [])
    memo.setdefault("findings", [])
    memo.setdefault("next_steps", [])
    return memo


def make_memo(
    loop: dict[str, Any],
    edges: list[dict[str, Any]],
    people: list[dict[str, Any]],
    use_llm: bool = True,
) -> dict[str, Any]:
    if use_llm and bedrock_ready():
        try:
            return llm_memo(loop, edges, people)
        except Exception as exc:
            memo = fallback_memo(loop, edges, people)
            memo["warning"] = f"Bedrock memo failed; fallback memo used. {exc}"
            return memo

    memo = fallback_memo(loop, edges, people)
    if use_llm:
        memo["warning"] = "BEDROCK_MODEL_ID was not set or AWS credentials were unavailable; fallback memo used."
    return memo


if __name__ == "__main__":
    fake_loop = {
        "loop_id": "demo-loop-1",
        "participant_count": 3,
        "total_flow": 125000,
        "bottleneck_amt": 42000,
        "loop_max_govt_share_pct": 0.63,
        "same_year": True,
    }
    fake_edges = [
        {"from_bn": "100000001", "to_bn": "100000002", "amount": 50000, "year": 2022},
        {"from_bn": "100000002", "to_bn": "100000003", "amount": 42000, "year": 2022},
    ]
    fake_people = [
        {"bn": "100000001", "charity_name": "North Program Foundation"},
        {"bn": "100000002", "charity_name": "Civic Learning Trust"},
        {"bn": "100000003", "charity_name": "Community Arts Fund"},
    ]
    print(json.dumps(make_memo(fake_loop, fake_edges, fake_people, use_llm=False), indent=2))
