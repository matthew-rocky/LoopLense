from __future__ import annotations

import json
import os
import re
from typing import Any


try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def bedrock_ready() -> bool:
    return bool(os.getenv("BEDROCK_MODEL_ID"))


def _session():
    import boto3

    profile = os.getenv("AWS_PROFILE")
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
    if profile:
        return boto3.Session(profile_name=profile, region_name=region)
    return boto3.Session(region_name=region)


def bedrock_client():
    return _session().client("bedrock-runtime")


def clean_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.I).strip()
    text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def converse_text(system: str, user: dict[str, Any] | str) -> str:
    if not bedrock_ready():
        raise RuntimeError("BEDROCK_MODEL_ID is not configured.")
    content = user if isinstance(user, str) else json.dumps(user, default=str)
    client = bedrock_client()
    res = client.converse(
        modelId=os.getenv("BEDROCK_MODEL_ID", ""),
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": content}]}],
        inferenceConfig={
            "maxTokens": _int_env("BEDROCK_MAX_TOKENS", 1200),
            "temperature": _float_env("BEDROCK_TEMPERATURE", 0.0),
        },
    )
    parts = res.get("output", {}).get("message", {}).get("content", [])
    return "\n".join(part.get("text", "") for part in parts if "text" in part).strip()


def plan_with_tool(question: str, tables: dict[str, list[str]], selected_loop: str | None) -> dict[str, Any]:
    if not bedrock_ready():
        raise RuntimeError("BEDROCK_MODEL_ID is not configured.")
    client = bedrock_client()
    tool_spec = {
        "toolSpec": {
            "name": "plan_looplens_answer",
            "description": "Create a safe DuckDB SELECT-only analytics plan for LoopLens local data.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "enum": [
                                "label_distribution",
                                "top_loops",
                                "largest_flow",
                                "government_exposure_by_label",
                                "charity_frequency",
                                "flow_distribution",
                                "selected_loop_explanation",
                                "selected_loop_participants",
                                "selected_loop_network",
                                "memo",
                                "unsupported",
                            ],
                        },
                        "sql": {"type": "string"},
                        "chart": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["bar", "histogram", "line", "scatter", "table", "metric", "distribution", "network", "none"],
                                },
                                "x": {"type": ["string", "null"]},
                                "y": {"type": ["string", "null"]},
                                "color": {"type": ["string", "null"]},
                                "title": {"type": "string"},
                            },
                            "required": ["type", "title"],
                        },
                        "summary": {"type": "string"},
                        "limit": {"type": "integer"},
                        "needs_selected_loop": {"type": "boolean"},
                        "safety_note": {"type": "string"},
                    },
                    "required": ["intent", "sql", "chart", "summary", "limit", "needs_selected_loop", "safety_note"],
                }
            },
        }
    }
    system = (
        "You are Ask LoopLens, a concise data assistant for a public-funding review-priority dashboard. "
        "Use only provided tables and columns. Return plans through the tool only. "
        "SQL must be SELECT-only and include no unsupported tables or columns. "
        "All numeric answers must come from executed data queries, not from memory. "
        "Do not accuse organizations of wrongdoing; use review priority, indicator, pattern, may warrant review, and human reviewer."
    )
    payload = {
        "question": question,
        "selected_loop": selected_loop,
        "tables": tables,
        "instruction": "Call plan_looplens_answer with the strict JSON plan. Numbers must come from DuckDB, not from memory.",
    }
    res = client.converse(
        modelId=os.getenv("BEDROCK_MODEL_ID", ""),
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": json.dumps(payload, default=str)}]}],
        toolConfig={"tools": [tool_spec], "toolChoice": {"tool": {"name": "plan_looplens_answer"}}},
        inferenceConfig={
            "maxTokens": _int_env("BEDROCK_MAX_TOKENS", 1200),
            "temperature": _float_env("BEDROCK_TEMPERATURE", 0.0),
        },
    )
    parts = res.get("output", {}).get("message", {}).get("content", [])
    for part in parts:
        tool = part.get("toolUse")
        if tool and tool.get("name") == "plan_looplens_answer":
            data = tool.get("input") or {}
            if isinstance(data, dict):
                return data
    text = "\n".join(part.get("text", "") for part in parts if "text" in part)
    return clean_json(text)


def load_memory(session_id: str) -> list[dict[str, str]]:
    table_name = os.getenv("MEMORY_TABLE_NAME")
    if not table_name:
        return []
    try:
        table = _session().resource("dynamodb").Table(table_name)
        item = table.get_item(Key={"session_id": session_id}).get("Item") or {}
        history = item.get("messages") or []
        return history if isinstance(history, list) else []
    except Exception:
        return []


def save_memory(session_id: str, messages: list[dict[str, str]]) -> None:
    table_name = os.getenv("MEMORY_TABLE_NAME")
    if not table_name:
        return
    try:
        table = _session().resource("dynamodb").Table(table_name)
        table.put_item(Item={"session_id": session_id, "messages": messages[-50:]})
    except Exception:
        return
