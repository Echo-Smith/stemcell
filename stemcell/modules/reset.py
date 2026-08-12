"""Reset 重置模块：清洗原始素材，提炼结构化底座。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..llm import LLMClient

PROMPT_TEMPLATE = """你是一个信息提炼专家。请将下面的原始输入材料，清洗并提炼为一份结构化的「任务底座」。

要求：
1. 剔除冗余、重复、无关的噪声信息
2. 保留核心目标、关键约束、重要事实、风格偏好
3. 输出严格的 JSON 格式，不要任何额外解释

JSON 结构：
{{
  "goal": "核心目标（一句话）",
  "constraints": ["约束条件1", "约束条件2"],
  "key_facts": ["关键事实1", "关键事实2"],
  "preferences": ["风格/偏好1", "风格/偏好2"],
  "boundaries": ["已知边界/不可逾越的红线"],
  "context_summary": "整体背景摘要（2-3句话）"
}}

原始输入材料：
---
{raw_input}
---
"""


class ResetModule:
    """重置模块：把原始输入归一化为通用底座。"""

    def __init__(self, llm: LLMClient, config: dict[str, Any] | None = None):
        self.llm = llm
        self.config = config or {}

    def run(self, raw_input: str) -> dict[str, Any]:
        """执行重置，返回结构化底座字典。"""
        prompt = PROMPT_TEMPLATE.format(raw_input=raw_input)
        result = self.llm.chat_json(
            prompt,
            system="你是一个严谨的信息提炼专家，只输出JSON。",
            model=self.config.get("reset_model"),
            temperature=0.3,
        )
        # 确保字段存在
        for key in ["goal", "constraints", "key_facts", "preferences", "boundaries", "context_summary"]:
            result.setdefault(key, [] if key.endswith("s") else "")
        return result

    def run_from_file(self, file_path: str | Path) -> dict[str, Any]:
        """从文件读取原始输入并执行重置。"""
        content = Path(file_path).read_text(encoding="utf-8")
        return self.run(content)
