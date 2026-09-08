"""Readable tradeoffs, without presenting an uncalibrated score as a winner."""

from __future__ import annotations

STATUS = {
    "reviewed": "模型未发现冲突（未实测）",
    "violates": "模型发现硬约束冲突",
    "needs_verification": "有约束待核实",
    "unassessed": "未评估",
    "excluded": "排除",
}


def inline(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def plan_markdown(plan: dict, title: str) -> str:
    lines = [f"### {title}", "", plan["summary"], ""]
    for label, key in (
        ("交付范围", "scope"),
        ("明确舍弃", "exclusions"),
        ("执行步骤", "steps"),
        ("风险", "risks"),
        ("代价", "tradeoffs"),
        ("适用条件", "choose_when"),
    ):
        lines += [f"**{label}**", ""] + [f"- {item}" for item in plan[key]] + [""]
    lines += [
        f"**工作量估计：** {plan['effort']['estimate']}",
        "",
        f"估计依据：{plan['effort']['basis']}",
        "",
    ]
    return "\n".join(lines)


def render_comparison(result: dict) -> str:
    rows = result["comparison"]
    lines = [
        "# 方案决策对比",
        "",
        result["base"]["goal"],
        "",
        "以下约束状态和建议由模型给出；分数不代表成功率，未知项需要核实。",
        "",
        "| 路线 | 交付范围 | 工作量估计 | 主要代价 | 适用条件 | 核对状态 |",
        "|---|---|---|---|---|---|",
    ]
    for i, candidate in enumerate(rows, 1):
        plan = candidate["plan"]
        cells = [
            f"{i}. {plan['title']}",
            "；".join(plan["scope"]),
            plan["effort"]["estimate"],
            "；".join(plan["tradeoffs"]),
            "；".join(plan["choose_when"]),
            STATUS[candidate["review_status"]],
        ]
        lines.append("| " + " | ".join(inline(v) for v in cells) + " |")
    if not rows:
        lines += ["", "没有成功生成的可比较方案。"]
    lines += ["", "## 按条件选择", ""]
    for i, candidate in enumerate(rows, 1):
        if candidate["review_status"] == "reviewed":
            lines.append(f"- 如果{'；'.join(candidate['plan']['choose_when'])}，可考虑路线 {i}。")
        else:
            lines.append(f"- 路线 {i}：{STATUS[candidate['review_status']]}，暂不作推荐。")
    for i, candidate in enumerate(rows, 1):
        lines += [
            "",
            plan_markdown(candidate["plan"], f"路线 {i}：{candidate['plan']['title']}"),
            f"**核对：** {STATUS[candidate['review_status']]}。{candidate['comment']}",
            "",
        ]
        for check in candidate["constraint_checks"]:
            lines.append(
                f"- {check['id']} / {check['status']}：{check['reason']}；候选证据：{check['evidence'] or '无'}"
            )
        for quote in candidate.get("missed_constraints", []):
            lines.append(f"- 底座可能遗漏的原文约束：{quote}")
    lines += ["", "## 任务约束与未知项", ""]
    for constraint in result["base"]["hard_constraints"]:
        lines.append(
            f"- {constraint['id']}：{constraint['text']}；原文：{constraint['source_quote']}"
        )
    for item in result["base"]["unknowns"]:
        lines.append(f"- 待确认：{item}")
    usage = result["usage"]
    lines += [
        "",
        "## 本次开销",
        "",
        f"调用 {usage['calls']} 次；耗时 {result['seconds']} 秒；输入 token：{usage['input_tokens'] if usage['input_tokens'] is not None else '未知'}；"
        f"输出 token：{usage['output_tokens'] if usage['output_tokens'] is not None else '未知'}。",
        "",
        f"费用估计：{usage['estimated_cost'] if usage['estimated_cost'] is not None else '未知（未提供计价或完整用量）'}。",
        "",
        "--top 仅限制 JSON 中的辅助排序集合，不减少调用，也不隐藏其他路线。",
    ]
    lines += [f"\n提示：{warning}" for warning in result["warnings"]]
    return "\n".join(lines) + "\n"
