"""Reproducible comparisons and blinded human review, with honest missing data."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import time
from collections import Counter
from pathlib import Path

from .pipeline import STRATEGIES
from .render import plan_markdown

RATING_FIELDS = [
    "case_id",
    "preferred_bundle",
    "reading_seconds",
    "constraint_misses",
    "meaningful_routes",
    "edits_needed",
    "adopted_bundle",
    "notes",
]

PROVIDER_STOP_ERRORS = {"RateLimitError", "AuthenticationError", "PermissionDeniedError"}


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_cases(path: Path, limit: int | None = None) -> list[dict]:
    values = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(values, list) or not values:
        raise ValueError("Cases must be a nonempty JSON list")
    seen, cases = set(), []
    for value in values:
        cid = value.get("id", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", cid) or cid in seen:
            raise ValueError("Case IDs must be unique safe filenames")
        seen.add(cid)
        if (
            value.get("kind") not in {"real", "synthetic"}
            or not isinstance(value.get("source"), str)
            or not value["source"].strip()
        ):
            raise ValueError("Each case needs kind=real/synthetic and a source")
        raw = value.get("input")
        if "input_file" in value:
            raw = (path.parent / value["input_file"]).read_text(encoding="utf-8")
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("Case needs nonempty input or input_file")
        cases.append(
            {
                "id": cid,
                "title": value.get("title", cid),
                "kind": value["kind"],
                "source": value["source"],
                "input": raw,
            }
        )
    return cases[:limit] if limit else cases


def run_benchmark(
    pipeline,
    cases: list[dict],
    output: Path,
    *,
    seed: int = 42,
    strategies: tuple[str, ...] = ("single_prompt", "sampling", "stemcell"),
    count: int = 3,
    offline: bool = False,
    progress=None,
) -> dict:
    if (
        not strategies
        or len(set(strategies)) != len(strategies)
        or any(s not in STRATEGIES for s in strategies)
    ):
        raise ValueError("Invalid benchmark strategies")
    if not 1 <= count <= 12:
        raise ValueError("count must be between 1 and 12")
    # All required calls are reserved conceptually before incurring any spend.
    expected_calls = len(cases) * (
        1 + sum((1 if s == "single_prompt" else count) + count for s in strategies)
    )
    if expected_calls > pipeline.ledger.max_calls - len(pipeline.ledger.records):
        raise ValueError(
            f"Benchmark requires up to {expected_calls} calls; increase max_calls or reduce cases"
        )
    if any(len(c["input"]) > pipeline.max_input_chars for c in cases):
        raise ValueError("A case exceeds max_input_chars")
    output.mkdir(parents=True, exist_ok=False)
    private = output / "private"
    private.mkdir(mode=0o700)
    packs = output / "blind"
    packs.mkdir()
    rng = random.Random(seed)
    summary = {
        "schema_version": "0.2",
        "offline": offline,
        "seed": seed,
        "expected_calls": expected_calls,
        "strategies": list(strategies),
        "cases": [],
        "human_results": None,
        "note": "Synthetic cases and offline simulations cannot establish user value.",
    }
    mappings, ratings = {}, []
    for case in cases:
        if progress:
            progress(f"{case['id']}：提炼共同评审底座")
        mark, started = len(pipeline.ledger.records), time.monotonic()
        entry = {
            "id": case["id"],
            "kind": case["kind"],
            "input_sha256": hashlib.sha256(case["input"].encode()).hexdigest(),
            "arms": {},
            "status": "complete",
        }
        try:
            base = pipeline.prepare(case["input"])
        except Exception as exc:
            entry.update(
                status="extraction_failed",
                error_type=type(exc).__name__,
                shared_usage=pipeline.ledger.summary(mark),
            )
            summary["cases"].append(entry)
            write_json(private / "summary.json", summary)
            if type(exc).__name__ in PROVIDER_STOP_ERRORS:
                summary["stopped_reason"] = type(exc).__name__
                break
            continue
        entry["shared_usage"] = pipeline.ledger.summary(mark)
        write_json(private / f"{case['id']}-source.json", {"case": case, "base": base})
        write_json(private / "summary.json", {**summary, "cases": summary["cases"] + [entry]})
        order = list(strategies)
        rng.shuffle(order)
        entry["execution_order"] = order
        for strategy in order:
            if progress:
                progress(f"{case['id']}：{strategy}")
            result = pipeline.run(case["input"], strategy=strategy, count=count, prepared_base=base)
            result["offline"] = offline
            entry["arms"][strategy] = result
            if result["status"] != "complete":
                entry["status"] = "partial"
            write_json(private / f"{case['id']}-{strategy}.json", result)
            # Durable checkpoint after each arm, including in-progress case.
            write_json(private / "summary.json", {**summary, "cases": summary["cases"] + [entry]})
            errors = {
                item.get("error_type") for item in result["candidates"] + result["comparison"]
            }
            if errors & PROVIDER_STOP_ERRORS:
                summary["stopped_reason"] = sorted(errors & PROVIDER_STOP_ERRORS)[0]
                entry["status"] = "partial"
                break
        labels = list(entry["arms"])
        rng.shuffle(labels)
        mappings[case["id"]] = {chr(65 + i): s for i, s in enumerate(labels)}
        lines = [
            f"# {case['id']} / {case['title']}",
            "",
            f"材料类型：{case['kind']}。",
            "",
            "离线协议模拟，不能评估方案质量。"
            if offline
            else "匿名比较：先选方案，再查看模型评分。",
            "",
            "## 原始需求",
            "",
            case["input"],
            "",
            "各组展示相同字段；不展示方法、模型评分和调用开销。内容风格仍可能泄露方法，不能保证完全盲法。",
        ]
        for label, strategy in mappings[case["id"]].items():
            lines += ["", f"## 方案组 {label}", ""]
            candidates = [c for c in entry["arms"][strategy]["candidates"] if c["status"] == "ok"]
            rng.shuffle(candidates)
            for i, candidate in enumerate(candidates, 1):
                # Generic title removes role labels; keep substance without paraphrasing.
                lines.append(plan_markdown(candidate["plan"], f"候选 {i}"))
            if not candidates:
                lines.append("本组没有成功生成的候选。")
        (packs / f"{case['id']}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        if entry["status"] == "complete":
            ratings.append({"case_id": case["id"]})
        entry["seconds"] = round(time.monotonic() - started, 3)
        summary["cases"].append(entry)
        write_json(private / "summary.json", summary)
        write_json(private / "mapping.json", mappings)
        if summary.get("stopped_reason"):
            break
    with (output / "ratings.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RATING_FIELDS)
        writer.writeheader()
        writer.writerows(ratings)
    (packs / "README.md").write_text(
        "# 盲评说明\n\n先阅读各案例文件，不打开 private 目录或总报告。方案组字母在每个案例中独立随机。\n\n"
        "填写上一级 ratings.csv：preferred_bundle 填 A/B/C（若有更多组按实际字母）、tie 或 neither；"
        "reading_seconds 填阅读与选择总秒数；constraint_misses、meaningful_routes、edits_needed 可按组写备注，"
        "如 A:1;B:0;C:2。adopted_bundle 等实际执行后再填。不要用模型分数代替个人选择。\n\n"
        "未填写保留为空。模拟案例不是用户实际需求，离线模拟内容不能用于偏好实验。\n",
        encoding="utf-8",
    )
    summary["usage"] = pipeline.ledger.summary()
    write_json(private / "summary.json", summary)
    (output / "REPORT.md").write_text(render_report(summary), encoding="utf-8")
    return summary


def render_report(summary: dict) -> str:
    lines = [
        "# Stemcell 初步实验报告",
        "",
        "**仅验证协议与工程行为，未调用真实模型。**"
        if summary["offline"]
        else "**真实接口运行；自动评审结果不等于真实用户价值。**",
        "",
        f"案例数：{len(summary['cases'])}；模拟案例：{sum(c['kind'] == 'synthetic' for c in summary['cases'])}。",
        "",
        "一次提示基线只在生成阶段调用一次；所有方法另接受相同评审。共同底座单独计费，每例只提炼一次。",
        "费用与 token 必须按实际记录比较；本报告没有证明各方法处于相同成本预算。",
        "",
        "| 方法 | 完整运行/尝试 | 有效生成 | 模型未发现冲突 | 约束待核实 | 约束冲突 | 未评估 | 调用数 | 输入 token | 输出 token |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for strategy in summary["strategies"]:
        arms = [c["arms"][strategy] for c in summary["cases"] if strategy in c["arms"]]
        states = Counter(item["review_status"] for arm in arms for item in arm["comparison"])

        def tokens(key, arms=arms):
            vals = [a["usage"][key] for a in arms]
            return sum(vals) if vals and all(v is not None for v in vals) else "未知"

        generated = sum(sum(c["status"] == "ok" for c in a["candidates"]) for a in arms)
        values = [
            strategy,
            f"{sum(a['status'] == 'complete' for a in arms)}/{len(arms)}",
            generated,
            states["reviewed"],
            states["needs_verification"],
            states["violates"],
            states["unassessed"],
            sum(a["usage"]["calls"] for a in arms),
            tokens("input_tokens"),
            tokens("output_tokens"),
        ]
        lines.append("| " + " | ".join(str(v) for v in values) + " |")
    shared = sum(c.get("shared_usage", {}).get("calls", 0) for c in summary["cases"])
    failed = [c["id"] for c in summary["cases"] if c["status"] == "extraction_failed"]
    lines += [
        "",
        "## 生成和评审开销分开看",
        "",
        "| 方法 | 生成调用 / token（输入+输出） | 评审调用 / token（输入+输出） | 平均运行秒数 |",
        "|---|---|---|---|",
    ]
    for strategy in summary["strategies"]:
        arms = [c["arms"][strategy] for c in summary["cases"] if strategy in c["arms"]]
        stage_cells = []
        for stage in ("generate", "judge"):
            records = [r for a in arms for r in a["usage"]["records"] if r["stage"] == stage]
            known = bool(records) and all(
                r["input_tokens"] is not None and r["output_tokens"] is not None for r in records
            )
            tokens = (
                str(sum(r["input_tokens"] + r["output_tokens"] for r in records))
                if known
                else "未知"
            )
            stage_cells.append(f"{len(records)} / {tokens}")
        seconds = round(sum(a["seconds"] for a in arms) / len(arms), 2) if arms else "无运行"
        lines.append(f"| {strategy} | {stage_cells[0]} | {stage_cells[1]} | {seconds} |")
    usage = summary.get("usage", {})
    lines += [
        "",
        f"全实验费用估计：{usage.get('estimated_cost') if usage.get('estimated_cost') is not None else '未知，缺少计价或完整用量'}。",
        "运行秒数不含共同底座提炼；并发度、限流和失败会影响时延。",
    ]
    lines += [
        "",
        f"共同提炼调用：{shared}。提炼失败案例：{', '.join(failed) or '无'}。",
        f"提前停止原因：{summary.get('stopped_reason', '无')}。不完整案例不纳入人工偏好统计。",
        "",
        "模型未发现冲突仅指模型给出的、程序能找到文字出处的判断；不代表约束实际实现或证据语义正确。",
        "完整运行指所需候选生成与评审均返回有效结构，不代表方案通过约束。",
        "",
        "## 尚不能回答",
        "",
        "- 哪个方法更受用户偏好、节省多少阅读时间：尚无人工盲评。",
        "- 哪个方案真的可执行、减少多少返工：尚无落地结果。",
        "- Stemcell 的提升是否来自更多计算：需要相近成本对照和组件消融。",
        "",
        "## 下一步",
        "",
        "先独立填写 ratings.csv，再运行 stemcell report。模拟需求需替换为有出处的实际需求。",
        "可用 stemcell_no_reset 作为生成阶段不提炼底座的消融组；共同评审仍使用同一底座和原文。",
        "完整结果和用量在 private/summary.json；不要在盲评前查看 private/mapping.json。",
    ]
    return "\n".join(lines) + "\n"


def report_ratings(output: Path) -> dict:
    summary = json.loads((output / "private" / "summary.json").read_text(encoding="utf-8"))
    mapping_path = output / "private" / "mapping.json"
    mappings = json.loads(mapping_path.read_text(encoding="utf-8")) if mapping_path.exists() else {}
    with (output / "ratings.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or any(k not in reader.fieldnames for k in RATING_FIELDS):
            raise ValueError("Invalid ratings CSV headers")
        rows = list(reader)
    choices, readings, seen = Counter(), [], set()
    complete_cases = {c["id"] for c in summary["cases"] if c["status"] == "complete"}
    for row in rows:
        cid = row["case_id"]
        if cid not in mappings or cid in seen:
            raise ValueError("Unknown or duplicate rated case")
        seen.add(cid)
        choice = row["preferred_bundle"].strip()
        if choice:
            if cid not in complete_cases:
                raise ValueError("Incomplete cases cannot support preference comparisons")
            if choice in {"tie", "neither"}:
                choices[choice] += 1
            elif choice in mappings[cid]:
                choices[mappings[cid][choice]] += 1
            else:
                raise ValueError("Unknown preferred bundle")
        if row["adopted_bundle"].strip() and row["adopted_bundle"].strip() not in {
            *mappings[cid],
            "neither",
        }:
            raise ValueError("Unknown adopted bundle")
        if row["reading_seconds"].strip():
            from .llm import finite_number

            readings.append(finite_number(float(row["reading_seconds"]), "reading_seconds"))
    if summary["offline"] and choices:
        raise ValueError("Offline placeholder content cannot support a human quality report")
    result = {
        "rated_cases": sum(choices.values()),
        "preferences": dict(choices),
        "reading_time_samples": len(readings),
        "mean_total_reading_seconds": sum(readings) / len(readings) if readings else None,
        "rows": rows,
    }
    summary["human_results"] = result
    write_json(output / "private" / "summary.json", summary)
    lines = [
        "# 人工盲评记录",
        "",
        f"已填写偏好：{result['rated_cases']} 个案例。",
        "",
        "以下是人工填表记录，不是模型分数；小样本不能作为确定性的产品结论。",
        "",
    ]
    if not choices:
        lines.append("尚无人工偏好，不能判断哪个方法更好。")
    else:
        for key, value in choices.items():
            lines.append(f"- {key}：{value} 次选择")
    lines += [
        "",
        f"总阅读时间均值：{result['mean_total_reading_seconds'] if readings else '未填写'} 秒；"
        "这是同时比较全部方法的总时间，不能推导各方法节省的时间。",
        "",
        "约束遗漏、路线差异、修改量和采纳备注保留在 ratings.csv，需逐案审阅。",
    ]
    (output / "HUMAN_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result
