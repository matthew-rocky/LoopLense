from __future__ import annotations

import copy
import json
import re
from typing import Any

try:
    from src.memo import make_memo
except ImportError:  # Allows `python src/verify.py` during quick local testing.
    from memo import make_memo


BLOCKED = [
    "fraud",
    "fraudulent",
    "corrupt",
    "corruption",
    "illegal",
    "criminal",
    "scheme",
    "scam",
    "money laundering",
    "proof of wrongdoing",
    "abuse",
    "suspicious",
    "laundering",
    "intentional misuse",
    "fake charity",
    "shell charity",
    "proves wrongdoing",
    "proves misuse",
    "guilty",
]

FINAL_STATUS = {
    "passed": "Verified",
    "mostly": "Mostly verified",
    "warning": "Needs review",
    "unsupported": "Unsupported",
    "failed": "Mismatch detected",
}

FIELDS = {
    "participants": ["participant_count", "participant_bns"],
    "flow": ["score_total_flow", "total_flow", "total_flow_allyears", "total_flow_window"],
    "bottleneck": ["score_bottleneck", "bottleneck_amt", "bottleneck_allyears", "bottleneck_window"],
    "govt": [
        "loop_max_govt_share_pct",
        "score_govt_share_pct",
        "max_govt_share_pct",
        "avg_govt_share_pct",
        "total_govt_all_years",
    ],
    "overhead": [
        "loop_max_strict_overhead_pct",
        "loop_max_broad_overhead_pct",
        "score_overhead_pct",
        "max_strict_overhead_pct",
        "max_broad_overhead_pct",
    ],
    "same_year": ["same_year", "score_same_year"],
    "repeat": ["max_participant_loop_count", "score_repeat_loops", "charity_total_loops"],
}


def get(row: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in row and row[name] not in (None, "", "nan", "NaN"):
            return row[name]
    return default


def has(row: dict[str, Any], name: str) -> bool:
    return name in row and row[name] not in (None, "", "nan", "NaN")


def nums(row: dict[str, Any], names: list[str]) -> dict[str, float]:
    found: dict[str, float] = {}
    for name in names:
        if not has(row, name):
            continue
        try:
            found[name] = float(row[name])
        except (TypeError, ValueError):
            continue
    return found


def claim_numbers(text: str) -> list[float]:
    found: list[float] = []
    for raw in re.findall(r"(?<![\w.])\$?\d[\d,]*(?:\.\d+)?%?", text):
        value = raw.replace("$", "").replace(",", "").replace("%", "")
        try:
            found.append(float(value))
        except ValueError:
            continue
    return found


def close(a: float, b: float) -> bool:
    candidates = [b]
    if 0 <= b <= 1:
        candidates.append(b * 100.0)
    if 0 <= a <= 1:
        candidates.append(b / 100.0)
    return any(abs(a - x) <= max(1.0, abs(x) * 0.03) for x in candidates)


def _check(
    name: str,
    status: str,
    claim: str,
    evidence: str,
    value: Any,
    explanation: str,
) -> dict[str, Any]:
    return {
        "check": name,
        "status": status,
        "claim": claim,
        "evidence": evidence,
        "evidence_value": "" if value is None else str(value),
        "explanation": explanation,
    }


def _claim_check(
    claim: str,
    status: str,
    field: str,
    value: Any,
    explanation: str,
) -> dict[str, Any]:
    return {
        "claim": claim,
        "status": status,
        "evidence_field": field,
        "evidence_value": "" if value is None else str(value),
        "explanation": explanation,
    }


def _rows(rows: Any) -> list[dict[str, Any]]:
    if rows is None:
        return []
    if isinstance(rows, list):
        return [r for r in rows if isinstance(r, dict)]
    if isinstance(rows, dict):
        return [rows]
    try:
        return rows.astype(object).where(rows.notnull(), None).to_dict("records")
    except Exception:
        return []


def _text_blob(rows: Any) -> str:
    parts: list[str] = []
    for row in _rows(rows):
        for value in row.values():
            if value is None:
                continue
            if isinstance(value, (list, tuple, set)):
                parts.extend(str(v) for v in value)
            else:
                parts.append(str(value))
    return " | ".join(parts)


def _numeric_values(rows: Any) -> list[tuple[str, float]]:
    vals: list[tuple[str, float]] = []
    row_list = _rows(rows)
    if row_list:
        vals.append(("row_count", float(len(row_list))))
    for row in row_list:
        for key, value in row.items():
            if value in (None, "", "nan", "NaN"):
                continue
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                vals.append((str(key), float(value)))
                continue
            if isinstance(value, str):
                try:
                    vals.append((str(key), float(value.replace(",", ""))))
                except ValueError:
                    pass
    return vals


def extract_numeric_claims(text: str) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    pattern = r"(?P<raw>\$?\d[\d,]*(?:\.\d+)?\s*(?:%|percent|participants?|loops?|charities?|records?|rows?)?)"
    for match in re.finditer(pattern, str(text or ""), re.I):
        raw = match.group("raw").strip()
        value_txt = re.sub(r"[^\d.]", "", raw.replace(",", ""))
        try:
            value = float(value_txt)
        except ValueError:
            continue
        unit = ""
        low = raw.lower()
        for candidate in ["%", "percent", "participant", "participants", "loop", "loops", "charity", "charities", "record", "records", "row", "rows"]:
            if candidate in low:
                unit = candidate
                break
        claims.append({"text": raw, "value": value, "unit": unit})
    return claims


def extract_entity_claims(text: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for bn in re.findall(r"\b\d{9}RR\d{4}\b", str(text or ""), re.I):
        key = bn.upper()
        if key not in seen:
            found.append({"type": "bn", "text": key})
            seen.add(key)
    for loop_id in re.findall(r"\b(?:loop|id)\s*[:#-]?\s*([A-Za-z0-9_.-]{1,40})", str(text or ""), re.I):
        key = str(loop_id)
        if key and key not in seen:
            found.append({"type": "loop_id", "text": key})
            seen.add(key)
    stop = {
        "LoopLens",
        "High",
        "Medium",
        "Low",
        "Review",
        "Priority",
        "The",
        "This",
        "These",
        "Selected",
        "Memo",
        "Evidence",
    }
    for name in re.findall(r"\b[A-Z][A-Za-z&.'-]*(?:\s+[A-Z][A-Za-z&.'-]*){1,5}\b", str(text or "")):
        cleaned = name.strip()
        if cleaned in stop or cleaned in seen:
            continue
        found.append({"type": "name", "text": cleaned})
        seen.add(cleaned)
    return found


def detect_risky_language(text: str, source_text: str | None = None) -> list[dict[str, Any]]:
    low = str(text or "").lower()
    source_low = str(source_text or "").lower()
    checks: list[dict[str, Any]] = []
    for term in BLOCKED:
        if term in low and term not in source_low:
            checks.append(
                _check(
                    "Risky language check",
                    "failed",
                    term,
                    "answer text",
                    term,
                    "Potentially accusatory language detected. LoopLens should use neutral review-priority wording.",
                )
            )
    return checks


def verify_numeric_claims(claims: list[dict[str, Any]], rows_used: Any) -> list[dict[str, Any]]:
    values = _numeric_values(rows_used)
    if not claims:
        return [_check("Numeric claim verification", "passed", "No numeric claims found", "rows used", len(_rows(rows_used)), "No numeric claims needed matching.")]
    checks: list[dict[str, Any]] = []
    if not values:
        return [_check("Numeric claim verification", "warning", "Numeric claim present", "rows used", "none", "No numeric evidence was attached.")]
    for claim in claims:
        value = float(claim["value"])
        matches = [(field, actual) for field, actual in values if close(value, actual)]
        if matches:
            field, actual = matches[0]
            checks.append(_check("Numeric claim verification", "passed", claim["text"], field, actual, "Numeric claim matched rows used within tolerance."))
        else:
            checks.append(_check("Numeric claim verification", "warning", claim["text"], "rows used", ", ".join(f"{f}={v:g}" for f, v in values[:8]), "Numeric claim was not matched to available rows."))
    return checks


def verify_entity_claims(claims: list[dict[str, str]], rows_used: Any) -> list[dict[str, Any]]:
    if not claims:
        return [_check("Entity claim verification", "passed", "No entity claims found", "rows used", len(_rows(rows_used)), "No named entity claims needed matching.")]
    blob = _text_blob(rows_used).lower()
    if not blob:
        return [_check("Entity claim verification", "warning", "Entity claim present", "rows used", "none", "No row text was attached for entity matching.")]
    checks: list[dict[str, Any]] = []
    for claim in claims:
        text = claim["text"]
        status = "passed" if text.lower() in blob else "warning"
        explanation = "Entity appears in rows used." if status == "passed" else "Entity was not found in rows used."
        checks.append(_check("Entity claim verification", status, text, "rows used", text if status == "passed" else "not found", explanation))
    return checks


def verify_label_claims(text: str, selected_loop_row: dict[str, Any] | None) -> list[dict[str, Any]]:
    labels = re.findall(r"\b(High|Medium|Low)\b", str(text or ""), re.I)
    if not labels:
        return [_check("Review label consistency", "passed", "No review label claim found", "selected loop", "", "No label claim needed matching.")]
    if not selected_loop_row:
        return [_check("Review label consistency", "warning", ", ".join(labels), "selected loop", "none", "No selected loop row was available for label checking.")]
    actual = get(selected_loop_row, "review_label", "label", default=None)
    if actual is None:
        return [_check("Review label consistency", "warning", ", ".join(labels), "selected loop", "missing label", "Selected loop row did not include a review label field.")]
    checks = []
    for label in labels:
        ok = str(label).lower() == str(actual).lower()
        checks.append(_check("Review label consistency", "passed" if ok else "failed", label, "selected_loop.review_label", actual, "Label claim matches selected loop." if ok else "Label claim does not match selected loop."))
    return checks


def verify_participant_count(text: str, participant_rows: Any) -> list[dict[str, Any]]:
    low = str(text or "").lower()
    if "participant" not in low and "charit" not in low:
        return [_check("Participant count consistency", "passed", "No participant count claim found", "participant rows", len(_rows(participant_rows)), "No participant-count claim needed matching.")]
    claims = [c for c in extract_numeric_claims(text) if c.get("unit") in {"participant", "participants", "charity", "charities"}]
    actual = len(_rows(participant_rows))
    if not claims:
        return [_check("Participant count consistency", "warning", "Participant reference without count", "participant rows", actual, "Participant claim did not include a clear count to verify.")]
    checks = []
    for claim in claims:
        ok = close(float(claim["value"]), float(actual))
        checks.append(_check("Participant count consistency", "passed" if ok else "failed", claim["text"], "participant rows", actual, "Participant count matches evidence." if ok else "Participant count does not match participant rows."))
    return checks


def verify_flow_claims(text: str, selected_loop_row: dict[str, Any] | None, edge_rows: Any) -> list[dict[str, Any]]:
    low = str(text or "").lower()
    if not any(word in low for word in ["flow", "amount", "transfer", "$"]):
        return [_check("Flow claim consistency", "passed", "No flow claim found", "flow evidence", "", "No flow claim needed matching.")]
    rows: list[dict[str, Any]] = []
    if selected_loop_row:
        rows.append(selected_loop_row)
    rows.extend(_rows(edge_rows))
    claims = extract_numeric_claims(text)
    money_claims = [c for c in claims if "$" in c["text"] or any(word in low for word in ["flow", "amount", "transfer"])]
    if not money_claims:
        return [_check("Flow claim consistency", "warning", "Flow reference without amount", "flow evidence", len(rows), "Flow claim did not include a clear amount to verify.")]
    values = _numeric_values(rows)
    checks = []
    for claim in money_claims:
        matches = [(field, actual) for field, actual in values if close(float(claim["value"]), actual)]
        if matches:
            field, actual = matches[0]
            checks.append(_check("Flow claim consistency", "passed", claim["text"], field, actual, "Flow or amount claim matched available evidence."))
        else:
            checks.append(_check("Flow claim consistency", "warning", claim["text"], "flow evidence", "not found", "Flow or amount claim was not matched to available evidence."))
    return checks


def build_verification_summary(checks: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = [str(c.get("status", "")).lower() for c in checks]
    if any(s in {"failed", "mismatch", "blocked"} for s in statuses):
        overall = "Mismatch detected"
        status = "failed"
    elif any(s in {"unsupported"} for s in statuses):
        overall = "Unsupported"
        status = "unsupported"
    elif any(s in {"warning", "partial", "not found"} for s in statuses):
        if any(s == "passed" for s in statuses):
            overall = "Mostly verified"
            status = "mostly"
        else:
            overall = "Needs review"
            status = "warning"
    elif checks:
        overall = "Verified"
        status = "passed"
    else:
        overall = "Needs review"
        status = "warning"
    return {
        "overall_status": overall,
        "status": status,
        "summary": (
            "This answer passed basic grounding checks against rows used."
            if status == "passed"
            else "This answer is mostly grounded in the rows used, with some checks that need human review."
            if status == "mostly"
            else "This request is unsupported by the current deterministic chat handlers."
            if status == "unsupported"
            else "This answer needs human review because some claims could not be matched or raised warnings."
        ),
    }


def verify_chat_answer(answer_text: str, rows_used: Any, data_context: dict[str, Any], intent: str) -> dict[str, Any]:
    row_list = _rows(rows_used)
    if intent == "unsupported":
        return {
            "overall_status": "Unsupported",
            "status": "unsupported",
            "summary": "This request is unsupported by the current deterministic chat handlers.",
            "rows_used_count": 0,
            "source": "unsupported request",
            "query_or_method_available": False,
            "checks": [
                _check(
                    "Intent support",
                    "unsupported",
                    "Unsupported request",
                    "chat router",
                    "unsupported",
                    "No deterministic LoopLens handler produced a grounded data answer for this request.",
                )
            ],
        }
    selected = data_context.get("selected_loop") if isinstance(data_context, dict) else None
    people = data_context.get("selected_people") if isinstance(data_context, dict) else []
    edges = data_context.get("selected_edges") if isinstance(data_context, dict) else []
    checks: list[dict[str, Any]] = [
        _check("Handler/query execution", "passed", intent, "handler", intent, "A deterministic LoopLens handler produced this response."),
        _check("Data grounding", "passed" if row_list else "warning", "Rows used attached", "rows_used", len(row_list), "Rows used are attached." if row_list else "No rows were attached for this answer."),
        _check("Visual grounding", "passed" if row_list or intent == "memo" else "warning", "Visual output generated from evidence", "chart/table", intent, "Visual output is based on attached rows or selected evidence."),
        _check("Method transparency", "passed", "Query or method available", "method", "available", "The response exposes query or method details."),
    ]
    checks.extend(verify_numeric_claims(extract_numeric_claims(answer_text), row_list))
    checks.extend(verify_entity_claims(extract_entity_claims(answer_text), row_list + _rows(people) + _rows(edges)))
    checks.extend(verify_label_claims(answer_text, selected if isinstance(selected, dict) else None))
    checks.extend(verify_participant_count(answer_text, people))
    checks.extend(verify_flow_claims(answer_text, selected if isinstance(selected, dict) else None, edges))
    checks.extend(detect_risky_language(answer_text, _text_blob(row_list + _rows(people) + _rows(edges))))
    summary = build_verification_summary(checks)
    return {
        **summary,
        "rows_used_count": len(row_list),
        "source": "deterministic handler" if intent != "memo" else "memo generator with deterministic verification",
        "query_or_method_available": True,
        "checks": checks,
    }


def _memo_text(memo: Any) -> str:
    if isinstance(memo, dict):
        parts = [str(memo.get("title", "")), str(memo.get("summary", "")), str(memo.get("rationale", ""))]
        parts.extend(str(x) for x in memo.get("findings", []) if x is not None)
        parts.extend(str(x) for x in memo.get("next_steps", []) if x is not None)
        return "\n".join(parts)
    return str(memo or "")


def verify_memo(
    memo_text: Any,
    selected_loop_row: dict[str, Any] | None,
    participant_rows: Any,
    edge_rows: Any,
    evidence_rows: Any,
) -> dict[str, Any]:
    text = _memo_text(memo_text)
    claim_checks: list[dict[str, Any]] = []
    loop = selected_loop_row or {}
    if loop:
        for field in ["loop_id", "review_label", "review_score", "total_flow", "bottleneck_amt", "loop_max_govt_share_pct", "loop_max_strict_overhead_pct"]:
            if field in loop and loop[field] not in (None, ""):
                claim_checks.append(_claim_check(field, "supported", field, loop[field], "Selected loop field is available as memo evidence."))
    else:
        claim_checks.append(_claim_check("selected loop", "not found", "selected_loop", "", "No selected loop row was available."))

    participant_n = len(_rows(participant_rows))
    claim_checks.append(_claim_check("participant rows", "supported" if participant_n else "not found", "participant_rows", participant_n, "Participant evidence row count."))
    edge_n = len(_rows(edge_rows))
    claim_checks.append(_claim_check("transfer edge rows", "supported" if edge_n else "not found", "edge_rows", edge_n, "Transfer edge evidence row count."))

    for check in verify_numeric_claims(extract_numeric_claims(text), [loop] + _rows(participant_rows) + _rows(edge_rows) + _rows(evidence_rows)):
        status = {"passed": "supported", "warning": "partially supported", "failed": "mismatch"}.get(check["status"], "partially supported")
        claim_checks.append(_claim_check(check["claim"], status, check["evidence"], check["evidence_value"], check["explanation"]))

    for check in verify_entity_claims(extract_entity_claims(text), [loop] + _rows(participant_rows) + _rows(edge_rows) + _rows(evidence_rows)):
        status = {"passed": "supported", "warning": "not found", "failed": "mismatch"}.get(check["status"], "not found")
        claim_checks.append(_claim_check(check["claim"], status, check["evidence"], check["evidence_value"], check["explanation"]))

    for risky in detect_risky_language(text, _text_blob([loop] + _rows(participant_rows) + _rows(edge_rows) + _rows(evidence_rows))):
        claim_checks.append(_claim_check(risky["claim"], "mismatch", risky["evidence"], risky["evidence_value"], risky["explanation"]))

    normalized = []
    for c in claim_checks:
        s = str(c.get("status", "")).lower()
        normalized.append({"status": "failed" if s in {"mismatch"} else "warning" if s in {"partially supported", "not found"} else "passed"})
    summary = build_verification_summary(normalized)
    return {
        **summary,
        "checks": claim_checks,
        "rows_used_count": 1 + participant_n + edge_n + len(_rows(evidence_rows)),
    }


def block(text: str) -> bool:
    low = text.lower()
    return any(term in low for term in BLOCKED)


def field_note(names: list[str]) -> str:
    return "Checked fields: " + ", ".join(names) + "."


def uniq_bns(people: list[dict[str, Any]]) -> set[str]:
    bns: set[str] = set()
    for person in people:
        bn = get(person, "bn", "BN", "charity_bn", "business_number")
        if bn is not None:
            bns.add(str(bn).strip())
    return {bn for bn in bns if bn}


def _as_list(x: Any) -> list[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, tuple):
        return list(x)
    if isinstance(x, str):
        return [part.strip() for part in re.split(r"[,;|]", x) if part.strip()]
    return [x]


def _count_note(loop: dict[str, Any], people: list[dict[str, Any]]) -> tuple[str, str, str]:
    sources: list[str] = []
    counts: list[int] = []

    raw_count = get(loop, "participant_count")
    if raw_count is not None:
        try:
            n = int(float(raw_count))
            counts.append(n)
            sources.append(f"participant_count={n}")
        except (TypeError, ValueError):
            sources.append("participant_count was present but not numeric")

    raw_bns = _as_list(get(loop, "participant_bns"))
    if raw_bns:
        n = len({str(bn).strip() for bn in raw_bns if str(bn).strip()})
        counts.append(n)
        sources.append(f"participant_bns={n}")

    people_bns = uniq_bns(people)
    if people_bns:
        counts.append(len(people_bns))
        sources.append(f"unique people BNs={len(people_bns)}")

    if not sources:
        return "Unsupported", "No participant count field or participant BN list was available.", (
            "Participant evidence was missing."
        )

    if len(set(counts)) > 1:
        return "Partial", "; ".join(sources), "Participant counts are present but do not fully match."
    return "Supported", "; ".join(sources), "Participant count evidence is available."


def support(
    kind: str,
    claim: dict[str, Any],
    loop: dict[str, Any],
    people: list[dict[str, Any]],
) -> tuple[str, str, str]:
    if kind == "neutral":
        return "Supported", "Neutral language does not require a numeric field.", "No factual risk claim to verify."

    if kind == "participants":
        return _count_note(loop, people)

    fields = FIELDS.get(kind, [])
    claim_fields = [f for f in claim.get("fields", []) if isinstance(f, str)]
    if claim_fields:
        fields = list(dict.fromkeys(fields + claim_fields))

    if not fields:
        return "Partial", "No known verification fields for this claim type.", "Claim type was not recognized."

    present = [name for name in fields if has(loop, name)]
    if not present:
        return "Unsupported", field_note(fields), "The selected loop evidence did not include these fields."

    values = nums(loop, present)
    if values:
        mentioned = claim_numbers(str(claim.get("text") or ""))
        evidence = "; ".join(f"{name}={value:g}" for name, value in values.items())
        if mentioned:
            unmatched = [n for n in mentioned if not any(close(n, value) for value in values.values())]
            if unmatched:
                return "Mismatch", evidence, (
                    "The claim contains numeric value(s) that do not match available evidence within tolerance: "
                    + ", ".join(f"{n:g}" for n in unmatched)
                    + "."
                )
            return "Supported", evidence, "Numeric claim matched selected loop fields within tolerance."
    else:
        evidence = "; ".join(f"{name}={loop[name]}" for name in present)

    return "Supported", evidence, "Claim is backed by selected loop fields."


def check_memo(
    memo: dict[str, Any],
    loop: dict[str, Any],
    edges: list[dict[str, Any]],
    people: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    claims = memo.get("claims") or []

    if not isinstance(claims, list):
        claims = []

    for i, claim in enumerate(claims, start=1):
        if not isinstance(claim, dict):
            continue

        cid = str(claim.get("id") or f"c{i}")
        text = str(claim.get("text") or "")
        kind = str(claim.get("type") or "neutral")

        if block(text):
            checks.append(
                {
                    "id": cid,
                    "claim": text,
                    "status": "Blocked",
                    "evidence": "Blocked language appeared in the claim.",
                    "note": "The memo cannot present accusations or conclusions of wrongdoing.",
                }
            )
            continue

        status, evidence, note = support(kind, claim, loop, people)
        checks.append({"id": cid, "claim": text, "status": status, "evidence": evidence, "note": note})

    if not checks:
        checks.append(
            {
                "id": "c0",
                "claim": "Memo contains no structured claims.",
                "status": "Partial",
                "evidence": "No claims list was available.",
                "note": "The memo can be shown, but claim-level verification is limited.",
            }
        )

    return checks


def _matches(text: str, claim: str) -> bool:
    low = text.lower()
    c = claim.lower()
    return bool(c and (c in low or low in c))


def clean_memo(memo: dict[str, Any], checks: list[dict[str, Any]]) -> dict[str, Any]:
    clean = copy.deepcopy(memo)
    blocked_ids = {c["id"] for c in checks if c.get("status") == "Blocked"}
    unsupported = {c["id"] for c in checks if c.get("status") in {"Blocked", "Unsupported"}}
    bad_claims = [str(c.get("claim") or "") for c in checks if c.get("status") in {"Blocked", "Unsupported"}]

    claims = clean.get("claims") or []
    if isinstance(claims, list):
        clean["claims"] = [
            claim
            for claim in claims
            if isinstance(claim, dict)
            and str(claim.get("id")) not in blocked_ids
            and str(claim.get("id")) not in unsupported
        ]
    else:
        clean["claims"] = []

    findings = clean.get("findings") or []
    kept: list[str] = []
    if isinstance(findings, list):
        for finding in findings:
            text = str(finding)
            if block(text):
                continue
            if any(_matches(text, claim) for claim in bad_claims):
                continue
            kept.append(text)
    clean["findings"] = kept

    if block(str(clean.get("summary") or "")):
        clean["summary"] = (
            "The selected loop may deserve human review based on available CRA records. "
            "This summary has been kept neutral because the original text used blocked language."
        )

    if block(str(clean.get("rationale") or "")):
        clean["rationale"] = (
            "The score is produced by deterministic data logic. The memo explains selected evidence "
            "and does not make legal or intent-based conclusions."
        )

    removed = len(blocked_ids) + len(unsupported - blocked_ids)
    if removed:
        clean["warning"] = (
            f"{removed} memo claim(s) were removed because they were blocked or unsupported by selected evidence."
        )
    else:
        clean.setdefault("warning", None)

    clean.setdefault(
        "disclaimer",
        "This memo is not a finding of wrongdoing. It is an evidence-based review-priority summary based on available CRA records.",
    )
    return clean


def build_memo(
    loop: dict[str, Any],
    edges: list[dict[str, Any]],
    people: list[dict[str, Any]],
    use_llm: bool = True,
) -> dict[str, Any]:
    memo = make_memo(loop, edges, people, use_llm=use_llm)
    checks = check_memo(memo, loop, edges, people)
    memo = clean_memo(memo, checks)
    safe = all(check["status"] not in {"Blocked", "Unsupported"} for check in checks)
    return {"memo": memo, "checks": checks, "safe": safe}


# Example usage:
# from src.verify import build_memo
#
# result = build_memo(loop, edges, people)
# memo = result["memo"]
# checks = result["checks"]


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
    print(json.dumps(build_memo(fake_loop, fake_edges, fake_people, use_llm=False), indent=2))
