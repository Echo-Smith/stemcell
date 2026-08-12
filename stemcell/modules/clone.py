"""Clone 克隆模块：基于底座派生多视角副本。"""

from __future__ import annotations

import json
from typing import Any

# 预设视角及其 prompt 前缀
PERSPECTIVES: dict[str, dict[str, str]] = {
    "conservative": {
        "label": "保守稳健",
        "prefix": "请以保守稳健的视角思考，优先考虑低风险、可验证、渐进式的方案，避免激进创新。",
    },
    "engineering": {
        "label": "工程落地",
        "prefix": "请以工程落地视角思考，重点关注技术可行性、实现成本、运维复杂度、可扩展性。",
    },
    "creative": {
        "label": "激进创新",
        "prefix": "请以激进创新视角思考，大胆突破常规，提出颠覆性、非显而易见的方案。",
    },
    "risk": {
        "label": "风险审计",
        "prefix": "请以风险审计视角思考，重点识别潜在风险、失败模式、安全隐患、合规问题。",
    },
    "user": {
        "label": "用户视角",
        "prefix": "请以最终用户视角思考，关注用户体验、学习成本、真实需求、使用场景。",
    },
    "competitor": {
        "label": "竞品视角",
        "prefix": "请以竞品分析视角思考，对比现有解决方案，寻找差异化和竞争优势。",
    },
    "minimal": {
        "label": "极简主义",
        "prefix": "请以极简主义视角思考，用最少的资源、最简单的方案解决核心问题，砍掉一切非必要。",
    },
    "scalable": {
        "label": "规模化",
        "prefix": "请以规模化视角思考，重点考虑方案在用户量、数据量、团队规模增长后的表现。",
    },
}


class CloneModule:
    """克隆模块：基于底座生成多视角副本。"""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    def run(
        self,
        base: dict[str, Any],
        perspectives: list[str] | None = None,
        count: int | None = None,
    ) -> list[dict[str, Any]]:
        """生成克隆副本列表。

        每个副本包含：底座信息 + 视角标签 + 视角prompt前缀。
        """
        perspectives = perspectives or self.config.get("default_perspectives", ["conservative", "engineering", "creative", "risk"])
        count = count or len(perspectives)

        # 如果 count 大于 perspectives 数量，循环复用视角
        selected = []
        for i in range(count):
            p = perspectives[i % len(perspectives)]
            selected.append(p)

        clones = []
        for idx, persp in enumerate(selected):
            meta = PERSPECTIVES.get(persp, {"label": persp, "prefix": f"请以{persp}视角思考。"})
            clone = {
                "id": f"clone_{idx:02d}",
                "perspective": persp,
                "perspective_label": meta["label"],
                "perspective_prefix": meta["prefix"],
                "base": base,
            }
            clones.append(clone)

        return clones

    @staticmethod
    def format_clone_context(clone: dict[str, Any]) -> str:
        """把一个克隆副本格式化为 LLM 可用的上下文文本。"""
        base = clone["base"]
        return (
            f"【视角】{clone['perspective_label']}\n"
            f"【视角指令】{clone['perspective_prefix']}\n\n"
            f"【任务底座】\n"
            f"目标：{base.get('goal', '')}\n"
            f"约束：{'; '.join(base.get('constraints', []))}\n"
            f"关键事实：{'; '.join(base.get('key_facts', []))}\n"
            f"偏好：{'; '.join(base.get('preferences', []))}\n"
            f"边界：{'; '.join(base.get('boundaries', []))}\n"
            f"背景：{base.get('context_summary', '')}\n"
        )
