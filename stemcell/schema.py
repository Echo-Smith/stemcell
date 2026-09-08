"""A parseable JSON object is not necessarily a valid result."""

from __future__ import annotations

import json


def text(value, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: non-empty text required")
    return value.strip()


def text_list(value, name: str, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{name}: list required")
    return [text(v, name) for v in value]


CANDIDATE_EXAMPLE = {
    "title": "路线标题",
    "summary": "核心做法",
    "scope": ["交付范围"],
    "exclusions": ["明确舍弃的能力"],
    "steps": ["可执行步骤"],
    "effort": {"estimate": "工作量估计或未知", "basis": "假设和估计依据"},
    "risks": ["最可能失败的地方"],
    "tradeoffs": ["为收益付出的代价"],
    "choose_when": ["适合选这条路线的具体条件"],
}


def validate_candidate(value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Candidate must be an object")
    result = {key: text(value.get(key), key) for key in ("title", "summary")}
    for key in ("scope", "exclusions", "steps", "risks", "tradeoffs", "choose_when"):
        result[key] = text_list(value.get(key), key, nonempty=True)
    effort = value.get("effort")
    if not isinstance(effort, dict):
        raise ValueError("effort must be an object")
    result["effort"] = {key: text(effort.get(key), key) for key in ("estimate", "basis")}
    return result


def candidate_content(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def validate_base(value: dict, raw: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Base must be an object")
    base = {key: text(value.get(key), key) for key in ("goal", "context_summary")}
    for key in ("constraints", "key_facts", "preferences", "boundaries", "unknowns"):
        base[key] = text_list(value.get(key), key)
    items = value.get("hard_constraints")
    if not isinstance(items, list):
        raise ValueError("hard_constraints must be a list")
    seen = set()
    validated = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("constraint must be an object")
        cid, claim, quote = [text(item.get(key), key) for key in ("id", "text", "source_quote")]
        if cid in seen or quote not in raw:
            raise ValueError("Duplicate constraint ID or ungrounded source quote")
        seen.add(cid)
        validated.append({"id": cid, "text": claim, "source_quote": quote})
    hard_text = {item["text"] for item in validated}
    if not set(base["constraints"] + base["boundaries"]).issubset(hard_text):
        raise ValueError("Every constraint/boundary must appear in hard_constraints")
    base["hard_constraints"] = validated
    base["raw_input"] = raw
    return base
