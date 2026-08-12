"""Quality 质控模块：多维度打分排序。"""

from __future__ import annotations

import json
from typing import Any

from ..llm import LLMClient

PROMPT_TEMPLATE = """你是一个严格的方案评审专家。请对以下候选方案进行多维度打分。

打分维度（每项 0-10 分）：
{dimensions_desc}

任务底座：
---
{base_summary}
---

候选方案（视角：{perspective_label}）：
---
{content}
---

请输出严格的 JSON，不要任何额外解释：
{{
  "scores": {{
    "feasibility": 0,
    "creativity": 0,
    "completeness": 0,
    "risk": 0
  }},
  "weighted_total": 0,
  "comment": "一句话点评"
}}

注意：risk 维度分数越高代表风险控制越好（低风险得高分）。
"""


class QualityModule:
    """质控模块：打分排序。"""

    def __init__(self, llm: LLMClient, config: dict[str, Any] | None = None):
        self.llm = llm
        self.config = config or {}
        self.dimensions = self.config.get(
            "dimensions",
            [
                {"name": "feasibility", "label": "可行性", "weight": 0.3},
                {"name": "creativity", "label": "创新性", "weight": 0.25},
                {"name": "completeness", "label": "完整性", "weight": 0.25},
                {"name": "risk", "label": "风险控制", "weight": 0.2},
            ],
        )

    def _dimensions_desc(self) -> str:
        lines = []
        for d in self.dimensions:
            lines.append(f"- {d['name']}（{d['label']}，权重 {d['weight']}）")
        return "\n".join(lines)

    def _base_summary(self, base: dict[str, Any]) -> str:
        return (
            f"目标：{base.get('goal', '')}\n"
            f"约束：{'; '.join(base.get('constraints', []))}\n"
            f"背景：{base.get('context_summary', '')}"
        )

    def score_single(self, candidate: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
        """对单个候选打分。"""
        if candidate["status"] == "error":
            return {
                **candidate,
                "scores": {d["name"]: 0 for d in self.dimensions},
                "weighted_total": 0,
                "comment": "生成失败，自动淘汰",
            }

        prompt = PROMPT_TEMPLATE.format(
            dimensions_desc=self._dimensions_desc(),
            base_summary=self._base_summary(base),
            perspective_label=candidate["perspective_label"],
            content=candidate["content"],
        )
        try:
            result = self.llm.chat_json(
                prompt,
                system="你是一个严格的方案评审专家，只输出JSON。",
                model=self.config.get("quality_model"),
                temperature=0.2,
            )
        except Exception:
            result = {
                "scores": {d["name"]: 5 for d in self.dimensions},
                "weighted_total": 5,
                "comment": "打分解析失败，给默认中分",
            }

        # 计算加权总分（如果模型没算对，重新算一遍）
        scores = result.get("scores", {})
        weighted = 0.0
        for d in self.dimensions:
            s = scores.get(d["name"], 0)
            weighted += s * d["weight"]

        return {
            **candidate,
            "scores": scores,
            "weighted_total": round(weighted, 2),
            "comment": result.get("comment", ""),
        }

    def run(
        self,
        candidates: list[dict[str, Any]],
        base: dict[str, Any],
        top_n: int | None = None,
    ) -> list[dict[str, Any]]:
        """批量打分并排序。"""
        scored = [self.score_single(c, base) for c in candidates]
        scored.sort(key=lambda x: x["weighted_total"], reverse=True)

        if top_n is not None:
            return scored[:top_n]
        return scored
